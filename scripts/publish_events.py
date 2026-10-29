"""One batch of outbox-to-Kafka dispatch; schedule externally."""
import os

from nexusgraph.event_outbox import send_pending

if os.getenv("NEXUSGRAPH_DATABASE_URL"):
    from nexusgraph import sqlstore as store

    sql_backend = True
else:
    from nexusgraph import store

    sql_backend = False


def main():
    store.initialize()
    delivered = send_pending(store, sql_backend=sql_backend)
    print({"published_events": delivered})


if __name__ == "__main__":
    main()
