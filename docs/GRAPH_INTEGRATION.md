# Optional Neo4j projection

Aetherion stores local demonstration data in SQLite; Neo4j is an optional
one-way graph analytics projection, not the authoritative database.

Run:
```bash
pip install -e '.[graph]'
export NEXUSGRAPH_NEO4J_URI='neo4j+s://your-managed-instance'
export NEXUSGRAPH_NEO4J_USER='neo4j'
export NEXUSGRAPH_NEO4J_PASSWORD='...'
export NEXUSGRAPH_EXPORT_TENANT='demo'
python scripts/project_neo4j.py
```

The projection uses tenant-qualified nodes and matching, parameterized queries,
and a composite uniqueness constraint. It replaces projected relationships
for a tenant, so run it against a **dedicated graph database** and back it up.
No real-world supplier information should be exported without approval.
Do not use an unencrypted connection for sensitive data.

For a production ingestion pipeline, add an idempotent outbox/CDC stream,
tenant authorization, retries, reconciliation, conflict handling and metrics.
