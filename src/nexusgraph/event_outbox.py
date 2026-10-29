"""Durable scenario events with optional Kafka delivery.

At-least-once delivery: Kafka consumers must deduplicate by event UUID.
Never put supplier details, documents or secret data into broker event payloads.
"""
from __future__ import annotations

import os

from sqlalchemy import text


def sql_pending(database, limit: int = 100) -> list[dict]:
    with database.db().connect() as conn:
        rows = conn.execute(text(
            "SELECT id,tenant,event_json FROM outbox WHERE published_at IS NULL "
            "ORDER BY created_at,id LIMIT :lim"
        ), dict(lim=limit)).mappings().all()
    return [dict(row) for row in rows]


def sql_mark_published(database, identifier: str):
    with database.db().begin() as conn:
        conn.execute(text(
            "UPDATE outbox SET published_at=:stamp "
            "WHERE id=:id AND published_at IS NULL"
        ), dict(id=identifier, stamp=database.timestamp()))


def sqlite_pending(database, limit: int = 100) -> list[dict]:
    with database.connect() as conn:
        rows = conn.execute(
            "SELECT id,tenant,event_json FROM outbox WHERE published_at IS NULL "
            "ORDER BY created_at,id LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def sqlite_mark_published(database, identifier: str):
    with database.connect() as conn:
        conn.execute(
            "UPDATE outbox SET published_at=? WHERE id=? AND published_at IS NULL",
            (database.timestamp(), identifier),
        )


def send_pending(database, sql_backend=False, producer=None, limit=100) -> int:
    """Publish one batch; mark only after delivery callback confirms the broker ack."""
    if not 1 <= limit <= 1000:
        raise ValueError("Batch must be between 1 and 1000")
    if producer is None:
        from confluent_kafka import Producer

        bootstrap = os.environ["NEXUSGRAPH_KAFKA_BOOTSTRAP"]
        producer = Producer({
            "bootstrap.servers": bootstrap,
            "security.protocol": os.getenv("NEXUSGRAPH_KAFKA_PROTOCOL", "SASL_SSL"),
            "sasl.mechanism": os.getenv("NEXUSGRAPH_KAFKA_SASL_MECHANISM", "PLAIN"),
            "sasl.username": os.getenv("NEXUSGRAPH_KAFKA_USER", ""),
            "sasl.password": os.getenv("NEXUSGRAPH_KAFKA_PASSWORD", ""),
            "enable.idempotence": True,
            "acks": "all",
        })
    pending = sql_pending(database, limit) if sql_backend else sqlite_pending(database, limit)
    mark = sql_mark_published if sql_backend else sqlite_mark_published
    topic = os.getenv("NEXUSGRAPH_KAFKA_TOPIC", "nexusgraph.events.v1")
    sent = 0
    for row in pending:
        result = {"delivered": False}

        def acknowledged(error, message, target=result):
            target["delivered"] = error is None

        producer.produce(
            topic=topic,
            key=row["id"],
            value=row["event_json"].encode("utf-8"),
            on_delivery=acknowledged,
        )
        producer.flush(timeout=10)
        if not result["delivered"]:
            break
        mark(database, row["id"])
        sent += 1
    return sent
