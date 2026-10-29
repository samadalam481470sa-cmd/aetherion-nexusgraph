"""One-shot export of a synthetic tenant graph to Neo4j.

Requires: pip install -e '.[graph]' and NEXUSGRAPH_NEO4J_URI/USER/PASSWORD.
"""
import os

from neo4j import GraphDatabase

from nexusgraph import registry_graph, store
from nexusgraph.neo4j_projection import project_graph


def main():
    tenant = os.getenv("NEXUSGRAPH_EXPORT_TENANT", "demo")
    uri = os.environ["NEXUSGRAPH_NEO4J_URI"]
    user = os.environ["NEXUSGRAPH_NEO4J_USER"]
    password = os.environ["NEXUSGRAPH_NEO4J_PASSWORD"]
    store.initialize()
    registry_graph.initialize_edges()
    snapshot = registry_graph.graph(tenant)
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        result = project_graph(driver, tenant, snapshot)
    print(result)


if __name__ == "__main__":
    main()
