"""Optional one-way graph projection into Neo4j.

Requires the neo4j extra and a configured secure Neo4j instance.
Projection is per tenant and uses parameters for all data values.
"""
from __future__ import annotations


def project_graph(driver, tenant: str, graph: dict) -> dict:
    if not isinstance(tenant, str) or not tenant:
        raise ValueError("Tenant required")
    if len(graph["suppliers"]) > 10000 or len(graph["dependencies"]) > 50000:
        raise ValueError("Projection exceeds safe batch size")

    def write(tx):
        tx.run(
            "CREATE CONSTRAINT nexus_supplier_identity IF NOT EXISTS "
            "FOR (s:NexusSupplier) REQUIRE (s.tenant,s.id) IS UNIQUE"
        ).consume()
        # Sync a graph snapshot; never remove nodes belonging to other tenants.
        tx.run(
            "MATCH (s:NexusSupplier {tenant:$tenant}) "
            "OPTIONAL MATCH (s)-[r:SUPPLIES]->(:NexusSupplier {tenant:$tenant}) "
            "DELETE r",
            tenant=tenant,
        ).consume()
        tx.run(
            "UNWIND $suppliers AS supplier "
            "MERGE (s:NexusSupplier {tenant:$tenant,id:supplier.id}) "
            "SET s.name=supplier.name,s.region=supplier.region,s.tier=supplier.tier",
            tenant=tenant,
            suppliers=graph["suppliers"],
        ).consume()
        tx.run(
            "UNWIND $edges AS edge "
            "MATCH (a:NexusSupplier {tenant:$tenant,id:edge.upstream}) "
            "MATCH (b:NexusSupplier {tenant:$tenant,id:edge.downstream}) "
            "MERGE (a)-[r:SUPPLIES {part:edge.part}]->(b) "
            "SET r.dependency=edge.dependency",
            tenant=tenant,
            edges=graph["dependencies"],
        ).consume()

    with driver.session() as session:
        session.execute_write(write)
    return {
        "tenant": tenant,
        "nodes_projected": len(graph["suppliers"]),
        "edges_projected": len(graph["dependencies"]),
    }
