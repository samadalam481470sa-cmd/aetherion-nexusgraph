# Architecture & security boundaries

## Implemented
- FastAPI exposes synthetic supply-chain graph analytics and bounded simulations.
- SQLite stores tenant-scoped supplier records, scenario artifacts and audit event metadata.
- The write/read registry API accepts `X-Tenant-ID`, `X-Actor-ID`, and optional `X-API-Key`.
- In protected mode a strong environment-provided API key is mandatory. Caller-provided tenant headers are **not independently authenticated** and do not establish secure multi-tenancy.
- A read-only browser demo uses embedded fictional graph records.

## Production gaps
**Do not host this prototype on a public endpoint or ingest sensitive information.**
For genuine enterprise multi-tenancy, derive tenant identity from validated OIDC token claims rather than mutable headers. Add per-tenant RBAC, authorization policy tests, secure secrets management, request rate limits, database migrations and PostgreSQL row-level security. Replace unauthenticated demo analytics and browser paths with an authenticated gateway. Add structured audit log shipping, key rotation, observability, backups, dependency scanning, and penetration testing.

## Model limitations
Risk propagation samples uncertainty in per-edge transfer weight; does not calibrate probability of disruption or recovery time. Alternative supplier capability matches do not validate qualification, capacity, export restrictions or contracting constraints. No automatic purchasing, operational control or classified data handling.

## Data flow
1. Synthetic network supplied by `engine.py`.
2. User submits a bounded simulation request.
3. Pure modeling engine calculates repeatable exposure samples.
4. Registry API optionally persists scenario result and audit record in local SQLite.
5. Tenant-filtered APIs allow retrieval of that data.

## Planned architecture
React/Next.js interface, OIDC gateway, PostgreSQL (tenant data), Neo4j (graph traversal), MongoDB (source documents), Kafka (event ingestion), OpenTelemetry/Prometheus (telemetry). These are roadmap components, **not currently implemented**.
