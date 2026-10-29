"""Optional MongoDB document-evidence archive.

Never store real controlled technical information or personal data in the demo.
Tenant is derived from verified identity when this module is invoked by OIDC API.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from uuid import uuid4


def archive_document(
    collection,
    tenant: str,
    actor: str,
    supplier_id: str,
    kind: str,
    payload: dict,
) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Document payload must be an object")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > 32_000:
        raise ValueError("Document exceeds 32 KB")
    identifier = str(uuid4())
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    record = {
        "_id": identifier,
        "tenant": tenant,
        "actor": actor,
        "supplier_id": supplier_id,
        "kind": kind,
        "payload": payload,
        "sha256": digest,
        "created_at": datetime.now(timezone.utc),
    }
    collection.insert_one(record)
    return {"id": identifier, "sha256": digest, "supplier_id": supplier_id, "kind": kind}


def list_documents(collection, tenant: str, supplier_id: str, limit: int = 25) -> list[dict]:
    cursor = collection.find(
        {"tenant": tenant, "supplier_id": supplier_id},
        {"payload": 0, "actor": 0},
    ).sort("created_at", -1).limit(limit)
    return [
        {"id": row["_id"], "kind": row["kind"], "sha256": row["sha256"],
         "created_at": row["created_at"].isoformat()}
        for row in cursor
    ]


def connect_collection():
    uri = os.getenv("NEXUSGRAPH_MONGO_URI")
    if not uri:
        raise RuntimeError("MongoDB document archive not configured")
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=3000, tz_aware=True)
    collection = client[os.getenv("NEXUSGRAPH_MONGO_DB", "nexusgraph")]["supplier_evidence"]
    collection.create_index([("tenant", 1), ("supplier_id", 1), ("created_at", -1)])
    return collection
