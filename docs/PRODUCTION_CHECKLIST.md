# Release gates — not yet certified or production-ready

Aetherion NexusGraph is an exploratory, synthetic-data product; no claim of airworthiness,
DoD approval, cybersecurity compliance, or fit for production procurement is made.

## Implemented prototype gates
- [x] Static directed-acyclic supplier graph validation
- [x] Bounded, reproducible Monte Carlo scenario API
- [x] Tenant-filtered registry graph and scenario history (SQLite)
- [x] Bearer OIDC signature, issuer, audience, expiration, tenant claim verification
- [x] API-key demo compatibility mode
- [x] Deterministic model-quality diagnostics
- [x] CI lint, tests, wheel packaging and Docker smoke test workflows (passing status not independently verified)

## Must pass before real customer deployment
- [ ] GitHub Actions confirmed green on default branch
- [ ] PostgreSQL migrations, tenant DB isolation and backup/restore disaster exercises
- [ ] Enforce authorization of tenant membership and roles, not just a signed tenant claim
- [ ] End-to-end identity-provider integration and key-rotation tests
- [ ] Restrict all routes, including demo routes, behind security controls
- [ ] Ingress rate limiting, WAF, request size and timeout enforcement
- [ ] Security scanning, SAST, dependency/SBOM review and external penetration assessment
- [ ] Audit export to tamper-evident storage
- [ ] Validated, licensed real-world supplier data connectors and data governance
- [ ] Proven model accuracy and drift monitoring on representative data
- [ ] Load/chaos testing and recovery time objective verification
- [ ] Controlled information handling assessment and legal/security sign-off

Do not use live production, classified, export-controlled, sensitive personnel or
customer-specific records until all appropriate protections and approvals are in place.
