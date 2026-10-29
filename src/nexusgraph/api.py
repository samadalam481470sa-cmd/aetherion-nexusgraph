"""Read-only synthetic network API and bounded risk simulations."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from nexusgraph.engine import DEPENDENCIES, SUPPLIERS, alternatives, criticality, simulate

app = FastAPI(
    title="Aetherion NexusGraph",
    description="Synthetic aerospace supply-chain risk intelligence prototype",
    version="0.1.0",
)


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
