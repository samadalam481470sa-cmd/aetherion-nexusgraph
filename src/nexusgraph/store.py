"""SQLite-backed, tenant-scoped scenario history and auditable supplier registry.

SQLite is deliberately the local development adapter; production should migrate to
PostgreSQL with row-level security and managed backups before handling customer data.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from nexusgraph.engine import SUPPLIERS


def database_path() -> str:
    return os.getenv("NEXUSGRAPH_DB_PATH", "/tmp/nexusgraph.sqlite3")


@contextmanager
def connect():
    path = database_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA busy_timeout = 10000")
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA journal_mode = WAL" if path != ":memory:" else "PRAGMA journal_mode = MEMORY")
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def initialize() -> None:
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS suppliers (
                tenant TEXT NOT NULL,
                id TEXT NOT NULL,
                name TEXT NOT NULL,
                region TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                tier INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant,id)
            );
            CREATE TABLE IF NOT EXISTS scenarios (
                id TEXT PRIMARY KEY,
                tenant TEXT NOT NULL,
                actor TEXT NOT NULL,
                created_at TEXT NOT NULL,
                request_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_scenarios_tenant_created
                ON scenarios(tenant,created_at DESC);
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                tenant TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                object_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_tenant_created
                ON audit_events(tenant,created_at DESC);
        """)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def audit(db: sqlite3.Connection, tenant: str, actor: str, action: str, object_id: str) -> None:
    db.execute(
        "INSERT INTO audit_events VALUES (?,?,?,?,?,?)",
        (str(uuid4()), tenant, actor, action, object_id, timestamp()),
    )


def seed(tenant: str, actor: str) -> int:
    with connect() as db:
        count = 0
        for supplier in SUPPLIERS:
            existing = db.execute(
                "SELECT 1 FROM suppliers WHERE tenant=? AND id=?", (tenant, supplier.id)
            ).fetchone()
            if existing:
                continue
            db.execute(
                "INSERT INTO suppliers VALUES (?,?,?,?,?,?,?)",
                (tenant, supplier.id, supplier.name, supplier.region,
                 json.dumps(supplier.capabilities), supplier.tier, timestamp()),
            )
            count += 1
        audit(db, tenant, actor, "seed_suppliers", str(count))
        return count


def list_suppliers(tenant: str) -> list[dict]:
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM suppliers WHERE tenant=? ORDER BY id", (tenant,)
        ).fetchall()
    return [
        {**dict(row), "capabilities": json.loads(row["capabilities"])}
        for row in rows
    ]


def upsert_supplier(tenant: str, actor: str, supplier: dict) -> dict:
    with connect() as db:
        db.execute(
            """INSERT INTO suppliers VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(tenant,id) DO UPDATE SET
               name=excluded.name, region=excluded.region,
               capabilities=excluded.capabilities, tier=excluded.tier,
               updated_at=excluded.updated_at""",
            (tenant, supplier["id"], supplier["name"], supplier["region"],
             json.dumps(supplier["capabilities"]), supplier["tier"], timestamp()),
        )
        audit(db, tenant, actor, "upsert_supplier", supplier["id"])
    return supplier


def save_scenario(tenant: str, actor: str, request: dict, result: dict) -> str:
    identifier = str(uuid4())
    with connect() as db:
        db.execute(
            "INSERT INTO scenarios VALUES (?,?,?,?,?,?)",
            (identifier, tenant, actor, timestamp(), json.dumps(request), json.dumps(result)),
        )
        audit(db, tenant, actor, "run_scenario", identifier)
    return identifier


def list_scenarios(tenant: str, limit: int = 25) -> list[dict]:
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM scenarios WHERE tenant=? ORDER BY created_at DESC LIMIT ?",
            (tenant, limit),
        ).fetchall()
    return [
        {**{k: row[k] for k in ("id", "actor", "created_at")},
         "request": json.loads(row["request_json"]),
         "result": json.loads(row["result_json"])}
        for row in rows
    ]


def list_audit(tenant: str, limit: int = 50) -> list[dict]:
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM audit_events WHERE tenant=? ORDER BY created_at DESC LIMIT ?",
            (tenant, limit),
        ).fetchall()
    return [dict(row) for row in rows]
