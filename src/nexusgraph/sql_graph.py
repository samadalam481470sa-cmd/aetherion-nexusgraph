"""SQLAlchemy-backed graph registry with tenant-scoped traversals."""
from __future__ import annotations

from collections import defaultdict, deque

from sqlalchemy import text

from nexusgraph import sqlstore


def initialize_edges():
    with sqlstore.db().begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS supplier_edges (
                tenant VARCHAR(64) NOT NULL,
                upstream VARCHAR(64) NOT NULL,
                downstream VARCHAR(64) NOT NULL,
                part VARCHAR(128) NOT NULL,
                dependency DOUBLE PRECISION NOT NULL CHECK(dependency BETWEEN 0 AND 1),
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant,upstream,downstream,part)
            )
        """))


def graph(tenant):
    with sqlstore.db().connect() as conn:
        suppliers = conn.execute(text(
            "SELECT id,name,region,tier FROM suppliers WHERE tenant=:tenant ORDER BY id"
        ), dict(tenant=tenant)).mappings().all()
        edges = conn.execute(text(
            "SELECT upstream,downstream,part,dependency FROM supplier_edges "
            "WHERE tenant=:tenant ORDER BY upstream,downstream,part"
        ), dict(tenant=tenant)).mappings().all()
    return {
        "suppliers": [dict(row) for row in suppliers],
        "dependencies": [dict(row) for row in edges],
    }


def upsert_edge(tenant, actor, edge):
    if edge["upstream"] == edge["downstream"]:
        raise ValueError("Self-dependency is prohibited")
    with sqlstore.db().begin() as conn:
        nodes = {
            row[0] for row in conn.execute(
                text("SELECT id FROM suppliers WHERE tenant=:tenant"), dict(tenant=tenant)
            )
        }
        if edge["upstream"] not in nodes or edge["downstream"] not in nodes:
            raise ValueError("Both suppliers must exist in tenant registry")
        pairs = [
            (row[0], row[1]) for row in conn.execute(
                text("SELECT upstream,downstream FROM supplier_edges WHERE tenant=:tenant"),
                dict(tenant=tenant),
            ) if not (row[0] == edge["upstream"] and row[1] == edge["downstream"])
        ]
        outgoing = defaultdict(list)
        indegree = {node: 0 for node in nodes}
        for source, target in pairs + [(edge["upstream"], edge["downstream"])]:
            outgoing[source].append(target)
            indegree[target] += 1
        queue = deque(node for node, degree in indegree.items() if degree == 0)
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for child in outgoing[node]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if visited != len(nodes):
            raise ValueError("Dependency would introduce a cycle")
        conn.execute(text("""
            INSERT INTO supplier_edges
            VALUES (:tenant,:upstream,:downstream,:part,:dependency,:updated)
            ON CONFLICT(tenant,upstream,downstream,part) DO UPDATE SET
            dependency=excluded.dependency,updated_at=excluded.updated_at
        """), dict(
            tenant=tenant, **edge, updated=sqlstore.timestamp(),
        ))
        sqlstore.audit(
            conn, tenant, actor, "upsert_edge",
            edge["upstream"] + "->" + edge["downstream"],
        )
    return edge


def criticality_for_tenant(tenant):
    snapshot = graph(tenant)
    nodes = [row["id"] for row in snapshot["suppliers"]]
    outgoing = defaultdict(list)
    indegree = {node: 0 for node in nodes}
    for edge in snapshot["dependencies"]:
        outgoing[edge["upstream"]].append(edge)
        indegree[edge["downstream"]] += 1
    queue = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for edge in outgoing[node]:
            indegree[edge["downstream"]] -= 1
            if indegree[edge["downstream"]] == 0:
                queue.append(edge["downstream"])
    scores = []
    for source in nodes:
        best = {source: 1.0}
        for node in order:
            for edge in outgoing[node]:
                influence = best.get(node, 0) * edge["dependency"]
                best[edge["downstream"]] = max(best.get(edge["downstream"], 0), influence)
        scores.append({
            "supplier_id": source,
            "downstream_influence": round(sum(
                influence for node, influence in best.items() if node != source
            ), 5),
            "reachable_buyers": len(best) - 1,
        })
    return sorted(scores, key=lambda row: -row["downstream_influence"])
