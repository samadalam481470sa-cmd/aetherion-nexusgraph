"""Read-only synthetic network API and bounded risk simulations."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from nexusgraph import document_archive, ingestion
from nexusgraph.backend import registry_graph, store

from nexusgraph.engine import DEPENDENCIES, SUPPLIERS, alternatives, criticality, simulate
from nexusgraph.security import Principal, authenticated_principal
from nexusgraph.telemetry import metrics, record_http
from nexusgraph.tenant_risk import simulate_graph


app = FastAPI(
    title="Aetherion NexusGraph",
    description="Synthetic aerospace supply-chain risk intelligence prototype",
    version="0.1.0",
)
app.middleware("http")(record_http)
app.add_api_route("/metrics", metrics, methods=["GET"], include_in_schema=False)


class ScenarioRequest(BaseModel):
    disrupted_supplier: str = Field(min_length=1, max_length=64)
    severity: float = Field(default=.8, ge=0, le=1)
    trials: int = Field(default=500, ge=1, le=10000)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


@app.get("/health")
def health():
    return {"status": "ok", "data_classification": "SYNTHETIC"}


@app.get("/api/v1/network")
def network():
    return {
        "classification": "SYNTHETIC",
        "suppliers": [vars(s) for s in SUPPLIERS],
        "dependencies": [vars(e) for e in DEPENDENCIES],
    }


@app.get("/api/v1/criticality")
def get_criticality():
    return {"rankings": criticality(), "method": "max_weighted_path_sum"}


@app.get("/api/v1/alternatives/{supplier_id}")
def get_alternatives(supplier_id: str):
    try:
        return {"source_supplier": supplier_id, "candidates": alternatives(supplier_id),
                "notice": "Capability match only. Qualification, capacity and approval unverified."}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/scenarios")
def run_scenario(request: ScenarioRequest):
    try:
        return simulate(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).with_name("index.html"))


class SupplierInput(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    name: str = Field(min_length=1, max_length=200)
    region: str = Field(min_length=2, max_length=32)
    capabilities: list[str] = Field(default_factory=list, max_length=30)
    tier: int = Field(ge=0, le=20)


@app.post("/api/v1/registry/seed")
def seed_registry(identity: Principal = Depends(authenticated_principal)):
    store.initialize()
    return {"inserted": store.seed(identity.tenant, identity.actor)}


@app.get("/api/v1/registry/suppliers")
def registry_suppliers(identity: Principal = Depends(authenticated_principal)):
    store.initialize()
    return {"suppliers": store.list_suppliers(identity.tenant)}


@app.put("/api/v1/registry/suppliers")
def registry_upsert(supplier: SupplierInput, identity: Principal = Depends(authenticated_principal)):
    store.initialize()
    return store.upsert_supplier(identity.tenant, identity.actor, supplier.model_dump())


@app.post("/api/v1/registry/scenarios")
def registry_scenario(request: ScenarioRequest, identity: Principal = Depends(authenticated_principal)):
    store.initialize()
    try:
        result = simulate(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    scenario_id = store.save_scenario(identity.tenant, identity.actor, request.model_dump(), result)
    return {"scenario_id": scenario_id, **result}


@app.get("/api/v1/registry/scenarios")
def registry_scenarios(limit: int = Query(default=25, ge=1, le=100), identity: Principal = Depends(authenticated_principal)):
    store.initialize()
    return {"scenarios": store.list_scenarios(identity.tenant, limit)}


@app.get("/api/v1/registry/audit")
def registry_audit(limit: int = Query(default=50, ge=1, le=100), identity: Principal = Depends(authenticated_principal)):
    store.initialize()
    return {"events": store.list_audit(identity.tenant, limit)}


class EdgeInput(BaseModel):
    upstream: str = Field(min_length=1, max_length=64)
    downstream: str = Field(min_length=1, max_length=64)
    part: str = Field(min_length=1, max_length=128)
    dependency: float = Field(ge=0, le=1)

@app.post("/api/v1/registry/edges")
def upsert_dependency(edge: EdgeInput, identity: Principal = Depends(authenticated_principal)):
    store.initialize()
    registry_graph.initialize_edges()
    try:
        return registry_graph.upsert_edge(identity.tenant, identity.actor, edge.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@app.get("/api/v1/registry/graph")
def tenant_graph(identity: Principal = Depends(authenticated_principal)):
    store.initialize()
    registry_graph.initialize_edges()
    return registry_graph.graph(identity.tenant)

@app.get("/api/v1/registry/criticality")
def tenant_criticality(identity: Principal = Depends(authenticated_principal)):
    store.initialize()
    registry_graph.initialize_edges()
    return {"rankings": registry_graph.criticality_for_tenant(identity.tenant)}


@app.post("/api/v1/registry/import-csv")
def registry_import_csv(payload: str, identity: Principal = Depends(authenticated_principal)):
    try:
        count = ingestion.import_suppliers(identity.tenant, identity.actor, payload, backend=store)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"imported": count}


@app.post("/api/v1/registry/simulate-graph")
def simulate_tenant_graph(
    request: ScenarioRequest, identity: Principal = Depends(authenticated_principal)
):
    store.initialize()
    registry_graph.initialize_edges()
    snapshot = registry_graph.graph(identity.tenant)
    try:
        result = simulate_graph(
            snapshot, request.disrupted_supplier, request.severity,
            request.trials, request.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    scenario_id = store.save_scenario(
        identity.tenant, identity.actor, request.model_dump(), result
    )
    return {"scenario_id": scenario_id, **result}


class EvidenceInput(BaseModel):
    supplier_id: str = Field(min_length=1, max_length=64)
    kind: str = Field(min_length=1, max_length=64)
    payload: dict

@app.post("/api/v1/registry/evidence")
def add_evidence(
    entry: EvidenceInput, identity: Principal = Depends(authenticated_principal)
):
    if os.getenv("NEXUSGRAPH_MODE") != "oidc":
        raise HTTPException(status_code=403, detail="OIDC mode required for evidence archive")
    store.initialize()
    if entry.supplier_id not in {s['id'] for s in store.list_suppliers(identity.tenant)}:
        raise HTTPException(status_code=404, detail="Supplier not found")
    try:
        collection = document_archive.connect_collection()
        return document_archive.archive_document(
            collection, identity.tenant, identity.actor,
            entry.supplier_id, entry.kind, entry.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/api/v1/registry/evidence/{supplier_id}")
def get_evidence(
    supplier_id: str, identity: Principal = Depends(authenticated_principal)
):
    if os.getenv("NEXUSGRAPH_MODE") != "oidc":
        raise HTTPException(status_code=403, detail="OIDC mode required for evidence archive")
    collection = document_archive.connect_collection()
    return {
        "documents": document_archive.list_documents(
            collection, identity.tenant, supplier_id
        )
    }
