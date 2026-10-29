# Optional Kafka event streaming

Every persisted scenario completion inserts a minimal `scenario.completed` event into
the SQL or SQLite outbox in the **same database transaction** as its result.
The event contains only a UUID, tenant identifier, event name and scenario UUID.

Install `pip install -e '.[kafka]'`, configure
`NEXUSGRAPH_KAFKA_BOOTSTRAP`, `NEXUSGRAPH_KAFKA_TOPIC`,
`NEXUSGRAPH_KAFKA_PROTOCOL` (defaults to SASL_SSL),
`NEXUSGRAPH_KAFKA_USER`, and `NEXUSGRAPH_KAFKA_PASSWORD`.
Then run `python scripts/publish_events.py` on a recurring worker schedule.

The worker waits for broker acknowledgement before marking each event as sent.
It delivers **at least once**; consumer deduplication by event UUID is required.
Production requires single-active dispatcher coordination, DLQ/retry policy,
retention, transactional observability, tenant authorization and secret rotation.
No live Kafka broker has been configured or verified by this repository.
