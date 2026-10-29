# Aetherion NexusGraph

**Aerospace supply-chain dependency intelligence — an unclassified, synthetic-data prototype.**

A running FastAPI service and browser dashboard for analyzing cascading supplier disruptions. Uses a directed supplier/parts graph, exposure propagation, alternative-source identification, and seeded Monte Carlo scenarios.

## Quick start
```bash
docker compose up --build
# Visit http://localhost:8000
# API docs: http://localhost:8000/docs
```

Without Docker:
```bash
pip install -e ".[dev]"
uvicorn nexusgraph.api:app --reload --app-dir src
```

Run tests: `pytest -q`

## Endpoints
- `GET /health`
- `GET /api/v1/network` — synthetic companies and directed sourcing links
- `GET /api/v1/criticality` — downstream influence ranking
- `POST /api/v1/scenarios` — seeded Monte Carlo disruption simulation
- `GET /api/v1/alternatives/{supplier_id}` — alternate source candidates for compatible parts

Example:
```bash
curl -X POST http://localhost:8000/api/v1/scenarios -H 'Content-Type: application/json' -d '{"disrupted_supplier":"SUP-002","severity":0.8,"trials":500,"seed":42}'
```

## Interpretation
Edges point from **upstream supplier to downstream buyer**. `dependency` is the fraction of a buyer's relevant inputs exposed to the supplier in this illustrative graph. For each scenario, an affected buyer's direct/transitive loss is approximated from incoming exposure and sampled transfer strengths, capped to 1. Results show average exposure and an empirical 95th percentile across reproducible trials. This is an exploratory relative-risk model, **not** an airworthiness, procurement, or financial decision engine.

## Security and development boundaries
All data is **fictional**; no controlled technical information, classified data, real procurement secrets or actual supplier ratings. CORS is intentionally not opened globally. Do not expose publicly without authentication, request limits, audit logging, tenant isolation, and security review. Never interpret simulation output as an official supplier rating.

## Roadmap
- [x] Directed dependency model, criticality ranking, scenario API
- [x] Reproducible Monte Carlo exposure propagation and tests
- [x] Browser-based network/risk dashboard
- [ ] PostgreSQL persistence, Alembic and tenant isolation
- [ ] OIDC authentication and fine-grained authorization
- [ ] Kafka ingestion and validated supplier connectors
- [ ] Bayesian posterior estimates and capacity-constrained optimization
- [ ] Model validation, drift monitoring and audit evidence
- [ ] Production telemetry, rate limiting and deployment hardening

Apache-2.0 license. Demo/prototype only.
