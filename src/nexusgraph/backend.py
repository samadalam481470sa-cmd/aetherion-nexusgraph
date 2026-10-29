"""Select the relational and graph backend once at process startup."""
from __future__ import annotations

import os

if os.getenv("NEXUSGRAPH_DATABASE_URL"):
    from nexusgraph import sql_graph as registry_graph
    from nexusgraph import sqlstore as store
else:
    from nexusgraph import registry_graph, store

__all__ = ["registry_graph", "store"]
