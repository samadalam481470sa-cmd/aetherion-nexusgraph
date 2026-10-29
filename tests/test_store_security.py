import pytest
from fastapi.testclient import TestClient

from nexusgraph.api import app

client = TestClient(app)


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUSGRAPH_DB_PATH", str(tmp_path / "local.db"))
    monkeypatch.setenv("NEXUSGRAPH_MODE", "demo")
    monkeypatch.delenv("NEXUSGRAPH_API_KEY", raising=False)


def test_tenant_isolation_and_audit(isolated_db):
    a = {"X-Tenant-ID": "tenantA", "X-Actor-ID": "analyst"}
    b = {"X-Tenant-ID": "tenantB"}
    assert client.post("/api/v1/registry/seed", headers=a).json()["inserted"] == 10
    assert len(client.get("/api/v1/registry/suppliers", headers=a).json()["suppliers"]) == 10
    assert client.get("/api/v1/registry/suppliers", headers=b).json()["suppliers"] == []
    result = client.post(
        "/api/v1/registry/scenarios", headers=a,
        json={"disrupted_supplier": "SUP-004", "severity": .6, "trials": 25},
    )
    assert result.status_code == 200, result.text
    assert "scenario_id" in result.json()
    assert len(client.get("/api/v1/registry/scenarios", headers=a).json()["scenarios"]) == 1
    assert client.get("/api/v1/registry/scenarios", headers=b).json()["scenarios"] == []
    actions = {row["action"] for row in client.get("/api/v1/registry/audit", headers=a).json()["events"]}
    assert "run_scenario" in actions
    assert "seed_suppliers" in actions


def test_protected_mode_requires_key(isolated_db, monkeypatch):
    monkeypatch.setenv("NEXUSGRAPH_MODE", "protected")
    monkeypatch.setenv("NEXUSGRAPH_API_KEY", "this-is-a-long-test-secret-value")
    url = "/api/v1/registry/suppliers"
    assert client.get(url, headers={"X-Tenant-ID": "a"}).status_code == 401
    assert client.get(url, headers={
        "X-Tenant-ID": "a", "X-API-Key": "this-is-a-long-test-secret-value"
    }).status_code == 200
    assert client.get(url, headers={
        "X-Tenant-ID": "demo", "X-API-Key": "this-is-a-long-test-secret-value"
    }).status_code == 400


def test_registry_validation(isolated_db):
    result = client.put("/api/v1/registry/suppliers", json={
        "id": "CUSTOM-1", "name": "Example Supplier", "region": "US",
        "capabilities": ["composites"], "tier": 1,
    })
    assert result.status_code == 200, result.text
    assert client.put("/api/v1/registry/suppliers", json={
        "id": "bad id", "name": "Invalid", "region": "US",
        "capabilities": [], "tier": 1,
    }).status_code == 422
    assert client.get("/api/v1/registry/scenarios?limit=1001").status_code == 422
