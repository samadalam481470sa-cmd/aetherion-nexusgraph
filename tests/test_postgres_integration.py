"""Run separately with NEXUSGRAPH_DATABASE_URL pointing at a disposable test database."""
import os

import pytest
from fastapi.testclient import TestClient

from nexusgraph.api import app


@pytest.mark.skipif(
    not os.getenv("NEXUSGRAPH_DATABASE_URL", "").startswith("postgresql"),
    reason="Requires PostgreSQL CI service",
)
def test_end_to_end_postgres_backend():
    client = TestClient(app)
    headers = {"X-Tenant-ID": "pg_integration"}
    assert client.post("/api/v1/registry/seed", headers=headers).status_code == 200
    suppliers = client.get("/api/v1/registry/suppliers", headers=headers)
    assert suppliers.status_code == 200
    assert len(suppliers.json()["suppliers"]) == 10
    edge = client.post("/api/v1/registry/edges", headers=headers, json={
        "upstream": "SUP-004", "downstream": "SUP-002",
        "part": "resin", "dependency": .65,
    })
    assert edge.status_code == 200, edge.text
    result = client.post("/api/v1/registry/simulate-graph", headers=headers, json={
        "disrupted_supplier": "SUP-004", "severity": .9, "trials": 50, "seed": 7,
    })
    assert result.status_code == 200, result.text
    assert result.json()["source"] == "tenant_graph"
    assert len(client.get("/api/v1/registry/scenarios", headers=headers).json()["scenarios"]) >= 1
    assert client.get("/api/v1/registry/suppliers", headers={
        "X-Tenant-ID": "pg_other"
    }).json()["suppliers"] == []
