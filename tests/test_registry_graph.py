import pytest
from fastapi.testclient import TestClient

from nexusgraph.api import app

client = TestClient(app)


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUSGRAPH_DB_PATH", str(tmp_path / "graph.db"))
    monkeypatch.setenv("NEXUSGRAPH_MODE", "demo")
    monkeypatch.delenv("NEXUSGRAPH_API_KEY", raising=False)


def test_graph_and_cycles(isolated):
    headers = {"X-Tenant-ID": "alpha"}
    for name in ("A", "B", "C"):
        r = client.put("/api/v1/registry/suppliers", headers=headers, json={
            "id": name, "name": name, "region": "US", "capabilities": [], "tier": 1,
        })
        assert r.status_code == 200, r.text
    assert client.post("/api/v1/registry/edges", headers=headers, json={
        "upstream": "A", "downstream": "B", "part": "widget", "dependency": .8,
    }).status_code == 200
    assert client.post("/api/v1/registry/edges", headers=headers, json={
        "upstream": "B", "downstream": "C", "part": "widget", "dependency": .5,
    }).status_code == 200
    assert client.post("/api/v1/registry/edges", headers=headers, json={
        "upstream": "C", "downstream": "A", "part": "widget", "dependency": .5,
    }).status_code == 409
    graph = client.get("/api/v1/registry/graph", headers=headers).json()
    assert len(graph["dependencies"]) == 2
    assert len(client.get("/api/v1/registry/criticality", headers=headers).json()["rankings"]) == 3
    assert client.get("/api/v1/registry/graph", headers={"X-Tenant-ID": "beta"}).json()["suppliers"] == []
