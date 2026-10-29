import pytest
from fastapi.testclient import TestClient

from nexusgraph.api import app
from nexusgraph.engine import (
    Dependency,
    Supplier,
    alternatives,
    criticality,
    simulate,
    validate_network,
)

client = TestClient(app)


def test_health_and_network():
    assert client.get("/health").json()["status"] == "ok"
    data = client.get("/api/v1/network").json()
    assert len(data["suppliers"]) == 10
    assert len(data["dependencies"]) == 10
    assert data["classification"] == "SYNTHETIC"


def test_scenario_reproducible():
    x = simulate("SUP-004", .8, trials=100, seed=42)
    assert x == simulate("SUP-004", .8, trials=100, seed=42)
    exposures = {r["supplier_id"]: r["mean_exposure"] for r in x["results"]}
    assert exposures["SUP-004"] == .8
    assert exposures["SUP-002"] > 0
    assert exposures["SUP-001"] > 0
    assert exposures["SUP-009"] == 0


def test_zero_severity_zero_exposure():
    assert all(r["mean_exposure"] == 0 for r in simulate("SUP-003", 0)["results"])


def test_validation_and_constraints():
    with pytest.raises(ValueError):
        simulate("unknown", .5)
    with pytest.raises(ValueError):
        simulate("SUP-001", 1.5)
    with pytest.raises(ValueError):
        simulate("SUP-001", .5, trials=10001)
    with pytest.raises(ValueError):
        Dependency("A", "B", 1.2, "part")
    nodes = (Supplier("A", "A", "US", (), 0), Supplier("B", "B", "US", (), 1))
    with pytest.raises(ValueError, match="Cyclic"):
        validate_network(nodes, (Dependency("A", "B", .5, "x"), Dependency("B", "A", .5, "y")))


def test_alternatives_are_unverified():
    candidates = alternatives("SUP-002")
    assert len(candidates) == 1
    assert candidates[0]["supplier_id"] == "SUP-007"
    assert candidates[0]["qualification_status"] == "NOT_VERIFIED"


def test_criticality_and_api_errors():
    assert len(criticality()) == 10
    assert client.get("/api/v1/alternatives/missing").status_code == 404
    assert client.post("/api/v1/scenarios", json={"disrupted_supplier": "SUP-001", "severity": 5}).status_code == 422
    assert client.post("/api/v1/scenarios", json={"disrupted_supplier": "missing"}).status_code == 404
    assert client.get("/").status_code == 200
