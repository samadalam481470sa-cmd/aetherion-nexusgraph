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

## Persistent registry (local development)
The prototype includes tenant-scoped SQLite storage for supplier records, stored scenario results and audit events. Set `NEXUSGRAPH_MODE=protected` and a random `NEXUSGRAPH_API_KEY` of at least 24 characters to require an API key on registry routes. In demo mode registry routes are unauthenticated; **do not expose the demo to the Internet**. The user-controlled tenant header is not cryptographically bound to identity; this is not enterprise-grade tenant isolation.

```bash
curl -X POST http://localhost:8000/api/v1/registry/seed -H 'X-Tenant-ID: example'
curl http://localhost:8000/api/v1/registry/suppliers -H 'X-Tenant-ID: example'
curl -X POST http://localhost:8000/api/v1/registry/scenarios -H 'X-Tenant-ID: example' -H 'Content-Type: application/json' -d '{"disrupted_supplier":"SUP-004","severity":0.7,"trials":100}'
curl http://localhost:8000/api/v1/registry/audit -H 'X-Tenant-ID: example'
```

## Endpoints
- `GET /health`
- `GET /api/v1/network` — synthetic companies and directed sourcing links
- `GET /api/v1/criticality` — downstream influence ranking
- `POST /api/v1/scenarios` — seeded Monte Carlo disruption simulation
- `GET /api/v1/alternatives/{supplier_id}` — alternate source candidates for compatible parts
- `POST /api/v1/registry/seed` — seed synthetic registry for the caller tenant
- `GET /api/v1/registry/suppliers` — retrieve tenant suppliers
- `PUT /api/v1/registry/suppliers` — create or update tenant supplier
- `POST /api/v1/registry/scenarios` — run and save a scenario
- `GET /api/v1/registry/scenarios` — list saved scenarios
- `GET /api/v1/registry/audit` — review registry audit metadata

Example:
```bash
curl -X POST http://localhost:8000/api/v1/scenarios -H 'Content-Type: application/json' -d '{"disrupted_supplier":"SUP-002","severity":0.8,"trials":500,"seed":42}'
```

## Interpretation
Edges point from **upstream supplier to downstream buyer**. `dependency` is the fraction of a buyer's relevant inputs exposed to the supplier in this illustrative graph. For each scenario, an affected buyer's direct/transitive loss is approximated from incoming exposure and sampled transfer strengths, capped to 1. Results show average exposure and an empirical 95th percentile across reproducible trials. This is an exploratory relative-risk model, **not** an airworthiness, procurement, or financial decision engine.

## Security and development boundaries
All seeded data is **fictional**; no controlled technical information, classified data, real procurement secrets or actual supplier ratings. CORS is intentionally not opened globally. Do not expose publicly without authentication, request limits, audit logging, tenant isolation, and security review. Never interpret simulation output as an official supplier rating.

## Roadmap
- [x] Directed dependency model, criticality ranking, scenario API
- [x] Reproducible Monte Carlo exposure propagation and tests
- [x] Browser-based network/risk dashboard
- [x] Local SQLite supplier registry, scenario history, and tenant-filtered audit metadata
- [x] Optional API key gate for demo registry operations
- [x] CI distribution packaging and Docker dashboard smoke tests
- [ ] PostgreSQL persistence, Alembic and genuine token-enforced tenant isolation
- [ ] OIDC authentication and fine-grained authorization
- [ ] Kafka ingestion and validated supplier connectors
- [ ] Bayesian posterior estimates and capacity-constrained optimization
- [ ] Model validation, drift monitoring and audit evidence
- [ ] Production telemetry, rate limiting and deployment hardening

Apache-2.0 license. Demo/prototype only.

See [architecture and security limitations](docs/ARCHITECTURE.md).
