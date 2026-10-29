# Optional MongoDB evidence archive

Install `pip install -e '.[mongo]'`. Configure `NEXUSGRAPH_MONGO_URI`
with an authenticated TLS MongoDB connection and set `NEXUSGRAPH_MONGO_DB`.
The archive stores a hash, creation timestamp, tenant, actor, supplier ID,
evidence type and JSON payload. Indexes support tenant-scoped supplier lookup.

Use only fictional test evidence until the application has fully verified
tenant authorization, retention policies, encryption, data minimization,
access logging, recovery and secure delete procedures. **No controlled data**.

The archive is optional and does not replace the SQL transactional registry.
Document hashes provide integrity evidence for the stored bytes but are not
equivalent to tamper-proof storage or signed provenance.
