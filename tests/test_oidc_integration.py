from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from nexusgraph.api import app
from nexusgraph.identity import Identity

client = TestClient(app)


@pytest.fixture()
def secured_env(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUSGRAPH_DB_PATH", str(tmp_path / "secured.db"))
    monkeypatch.setenv("NEXUSGRAPH_MODE", "oidc")
    monkeypatch.setenv("NEXUSGRAPH_METRICS_TOKEN", "test-metrics-secret")


def test_spoofed_tenant_header_cannot_override_signed_identity(secured_env):
    with patch("nexusgraph.security.verify_token", return_value=Identity("signed_tenant", "user123")):
        response = client.post("/api/v1/registry/seed", headers={
            "Authorization": "Bearer mock-signed-token",
            "X-Tenant-ID": "attacker_tenant",
        })
        assert response.status_code == 200, response.text
        response = client.get("/api/v1/registry/suppliers", headers={
            "Authorization": "Bearer mock-signed-token",
            "X-Tenant-ID": "attacker_tenant",
        })
        assert len(response.json()["suppliers"]) == 10
    assert client.get("/api/v1/registry/suppliers", headers={
        "X-Tenant-ID": "signed_tenant",
    }).status_code == 401


def test_metrics_require_separate_secret(secured_env):
    assert client.get("/metrics").status_code == 401
    result = client.get("/metrics", headers={"X-Metrics-Token": "test-metrics-secret"})
    assert result.status_code == 200
    assert "nexusgraph_http_requests_total" in result.text
    assert result.headers["x-content-type-options"] == "nosniff"
