"""SQLAlchemy relational backend, compatible with PostgreSQL and SQLite.

Enable by setting NEXUSGRAPH_DATABASE_URL before the API process starts.
Database-level row security, roles and operational migrations remain deployment gates.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from sqlalchemy import create_engine, text

from nexusgraph.engine import SUPPLIERS


@lru_cache(maxsize=4)
def engine(url: str):
    return create_engine(url, pool_pre_ping=True, future=True)


def db():
    url = os.environ.get("NEXUSGRAPH_DATABASE_URL")
    if not url:
        raise RuntimeError("NEXUSGRAPH_DATABASE_URL is required for SQL backend")
    return engine(url)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def initialize():
    statements = [
        """CREATE TABLE IF NOT EXISTS suppliers (
        tenant VARCHAR(64) NOT NULL, id VARCHAR(64) NOT NULL,
        name VARCHAR(200) NOT NULL, region VARCHAR(32) NOT NULL,
        capabilities TEXT NOT NULL, tier INTEGER NOT NULL,
        updated_at TEXT NOT NULL, PRIMARY KEY(tenant,id))""",
        """CREATE TABLE IF NOT EXISTS scenarios (
        id VARCHAR(36) PRIMARY KEY, tenant VARCHAR(64) NOT NULL,
        actor VARCHAR(200) NOT NULL, created_at TEXT NOT NULL,
        request_json TEXT NOT NULL,result_json TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS audit_events (
        id VARCHAR(36) PRIMARY KEY, tenant VARCHAR(64) NOT NULL,
        actor VARCHAR(200) NOT NULL, action VARCHAR(64) NOT NULL,
        object_id VARCHAR(200) NOT NULL, created_at TEXT NOT NULL)""",
        "CREATE INDEX IF NOT EXISTS idx_sql_scenarios_tenant ON scenarios(tenant,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_sql_audit_tenant ON audit_events(tenant,created_at)",
    ]
    with db().begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def audit(conn, tenant, actor, action, object_id):
    conn.execute(
        text("INSERT INTO audit_events VALUES (:id,:tenant,:actor,:action,:obj,:created)"),
        dict(id=str(uuid4()), tenant=tenant, actor=actor, action=action,
             obj=object_id, created=timestamp()),
    )


def seed(tenant, actor):
    count = 0
    with db().begin() as conn:
        for supplier in SUPPLIERS:
            existing = conn.execute(
                text("SELECT 1 FROM suppliers WHERE tenant=:tenant AND id=:id"),
                dict(tenant=tenant, id=supplier.id),
            ).first()
            if existing:
                continue
            conn.execute(text(
                "INSERT INTO suppliers VALUES (:tenant,:id,:name,:region,:caps,:tier,:updated)"
            ), dict(
                tenant=tenant, id=supplier.id, name=supplier.name,
                region=supplier.region, caps=json.dumps(supplier.capabilities),
                tier=supplier.tier, updated=timestamp(),
            ))
            count += 1
        audit(conn, tenant, actor, "seed_suppliers", str(count))
    return count


def list_suppliers(tenant):
    with db().connect() as conn:
        records = conn.execute(text(
            "SELECT * FROM suppliers WHERE tenant=:tenant ORDER BY id"
        ), dict(tenant=tenant)).mappings().all()
    return [{**dict(row), "capabilities": json.loads(row["capabilities"])} for row in records]


def upsert_supplier(tenant, actor, supplier):
    params = dict(
        tenant=tenant, id=supplier["id"], name=supplier["name"],
        region=supplier["region"], caps=json.dumps(supplier["capabilities"]),
        tier=supplier["tier"], updated=timestamp(),
    )
    with db().begin() as conn:
        conn.execute(text("""
            INSERT INTO suppliers VALUES (:tenant,:id,:name,:region,:caps,:tier,:updated)
            ON CONFLICT(tenant,id) DO UPDATE SET name=excluded.name,
            region=excluded.region,capabilities=excluded.capabilities,
            tier=excluded.tier,updated_at=excluded.updated_at
        """), params)
        audit(conn, tenant, actor, "upsert_supplier", supplier["id"])
    return supplier


def save_scenario(tenant, actor, request, result):
    identifier = str(uuid4())
    with db().begin() as conn:
        conn.execute(text(
            "INSERT INTO scenarios VALUES (:id,:tenant,:actor,:created,:request,:result)"
        ), dict(
            id=identifier, tenant=tenant, actor=actor, created=timestamp(),
            request=json.dumps(request), result=json.dumps(result),
        ))
        audit(conn, tenant, actor, "run_scenario", identifier)
    return identifier


def list_scenarios(tenant, limit=25):
    with db().connect() as conn:
        rows = conn.execute(text(
            "SELECT * FROM scenarios WHERE tenant=:tenant ORDER BY created_at DESC LIMIT :lim"
        ), dict(tenant=tenant, lim=limit)).mappings().all()
    return [
        dict(id=row["id"], actor=row["actor"], created_at=row["created_at"],
             request=json.loads(row["request_json"]),
             result=json.loads(row["result_json"]))
        for row in rows
    ]


def list_audit(tenant, limit=50):
    with db().connect() as conn:
        rows = conn.execute(text(
            "SELECT * FROM audit_events WHERE tenant=:tenant ORDER BY created_at DESC LIMIT :lim"
        ), dict(tenant=tenant, lim=limit)).mappings().all()
    return [dict(row) for row in rows]
