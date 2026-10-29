"""Tenant-scoped dependency edge persistence and graph validation."""
from __future__ import annotations

from collections import defaultdict, deque

from nexusgraph.store import audit, connect, timestamp


def initialize_edges():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS supplier_edges (
                tenant TEXT NOT NULL,
                upstream TEXT NOT NULL,
                downstream TEXT NOT NULL,
                part TEXT NOT NULL,
                dependency REAL NOT NULL CHECK(dependency BETWEEN 0 AND 1),
                updated_at TEXT NOT NULL,
                PRIMARY KEY(tenant,upstream,downstream,part)
            )
        """)


def graph(tenant: str) -> dict:
    with connect() as db:
        suppliers = [
            dict(row) for row in db.execute(
                "SELECT id,name,region,tier FROM suppliers WHERE tenant=? ORDER BY id", (tenant,)
            )
        ]
        edges = [
            dict(row) for row in db.execute(
                "SELECT upstream,downstream,part,dependency FROM supplier_edges "
                "WHERE tenant=? ORDER BY upstream,downstream,part", (tenant,)
            )
        ]
    return {"suppliers": suppliers, "dependencies": edges}


def upsert_edge(tenant: str, actor: str, edge: dict) -> dict:
    if edge["upstream"] == edge["downstream"]:
        raise ValueError("Self-dependency is prohibited")
    with connect() as db:
        known = {
            row["id"] for row in db.execute(
                "SELECT id FROM suppliers WHERE tenant=?", (tenant,)
            )
        }
        if edge["upstream"] not in known or edge["downstream"] not in known:
            raise ValueError("Both suppliers must exist in tenant registry")
        existing = [
            (row["upstream"], row["downstream"]) for row in db.execute(
                "SELECT upstream,downstream FROM supplier_edges WHERE tenant=?", (tenant,)
            )
            if not (
                row["upstream"] == edge["upstream"]
                and row["downstream"] == edge["downstream"]
            )
        ]
        outgoing = defaultdict(list)
        indegree = {key: 0 for key in known}
        for upstream, downstream in existing + [(edge["upstream"], edge["downstream"])]:
            outgoing[upstream].append(downstream)
            indegree[downstream] += 1
        queue = deque(k for k, degree in indegree.items() if degree == 0)
        count = 0
        while queue:
            item = queue.popleft()
            count += 1
            for next_id in outgoing[item]:
                indegree[next_id] -= 1
                if indegree[next_id] == 0:
                    queue.append(next_id)
        if count != len(known):
            raise ValueError("Dependency would introduce a cycle")
        db.execute(
            """INSERT INTO supplier_edges VALUES (?,?,?,?,?,?)
               ON CONFLICT(tenant,upstream,downstream,part) DO UPDATE SET
               dependency=excluded.dependency,updated_at=excluded.updated_at""",
            (tenant, edge["upstream"], edge["downstream"], edge["part"],
             edge["dependency"], timestamp()),
        )
        audit(db, tenant, actor, "upsert_edge", edge["upstream"] + "->" + edge["downstream"])
    return edge


def criticality_for_tenant(tenant: str) -> list[dict]:
    snapshot = graph(tenant)
    nodes = [row["id"] for row in snapshot["suppliers"]]
    outgoing = defaultdict(list)
    indegree = {key: 0 for key in nodes}
    for edge in snapshot["dependencies"]:
        outgoing[edge["upstream"]].append(edge)
        indegree[edge["downstream"]] += 1
    queue = deque(sorted(key for key, n in indegree.items() if n == 0))
    order = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for edge in outgoing[current]:
            nxt = edge["downstream"]
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    scores = []
    for source in nodes:
        best = {source: 1.0}
        for node in order:
            for edge in outgoing[node]:
                candidate = best.get(node, 0) * edge["dependency"]
                if candidate > best.get(edge["downstream"], 0):
                    best[edge["downstream"]] = candidate
        scores.append({
            "supplier_id": source,
            "downstream_influence": round(sum(
                weight for key, weight in best.items() if key != source
            ), 5),
            "reachable_buyers": len(best) - 1,
        })
    return sorted(scores, key=lambda value: -value["downstream_influence"])
