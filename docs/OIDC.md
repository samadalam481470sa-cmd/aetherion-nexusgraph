# OIDC protected mode

Set `NEXUSGRAPH_MODE=oidc`, `NEXUSGRAPH_OIDC_ISSUER`, `NEXUSGRAPH_OIDC_AUDIENCE`, `NEXUSGRAPH_OIDC_JWKS_URL` to use identity-provider-issued RS256 bearer tokens.

The API validates signatures against an HTTPS JWKS, issuer, audience, expiration and required claims. It takes `tenant_id` from the verified token, never from a caller-supplied tenant header, and `sub` as the audit actor. Configure the identity provider to issue tenant-scoped `tenant_id` claims using a trusted authorization mapping, not self-service profile metadata.

**Limitations:** This is an integration foundation, not a full authorization architecture. It does not yet provide roles, tenant-wide access policies, immutable audit storage, rate limiting, token revocation or production-grade defense compliance. Validate authorization against your own identity provider and threat model before deployment.

The public synthetic-demo routes remain intentionally unauthenticated. Do not deploy the application publicly to handle confidential or controlled information.
