"""Scenario propagation on a tenant-owned directed supplier graph."""
from __future__ import annotations

from collections import defaultdict, deque
from math import ceil
from random import Random
from statistics import mean


def simulate_graph(
    graph: dict, supplier_id: str, severity: float, trials: int, seed: int
) -> dict:
    nodes = {supplier["id"] for supplier in graph["suppliers"]}
    if supplier_id not in nodes:
        raise ValueError("Disrupted supplier not found in this tenant's graph")
    if not 0 <= severity <= 1 or not 1 <= trials <= 10000:
        raise ValueError("Invalid scenario parameters")
    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    indegree = dict.fromkeys(nodes, 0)
    for edge in graph["dependencies"]:
        if edge["upstream"] not in nodes or edge["downstream"] not in nodes:
            raise ValueError("Graph references an unknown supplier")
        incoming[edge["downstream"]].append(edge)
        outgoing[edge["upstream"]].append(edge["downstream"])
        indegree[edge["downstream"]] += 1
    queue = deque(sorted(node for node in nodes if indegree[node] == 0))
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for next_node in sorted(outgoing[node]):
            indegree[next_node] -= 1
            if indegree[next_node] == 0:
                queue.append(next_node)
    if len(order) != len(nodes):
        raise ValueError("Graph has a cycle")
    random = Random(seed)
    outcomes: dict[str, list[float]] = {node: [] for node in order}
    for _ in range(trials):
        losses = {node: 0.0 for node in order}
        losses[supplier_id] = severity
        for node in order:
            if node == supplier_id:
                continue
            unaffected = 1.0
            for edge in incoming[node]:
                transmission = min(1.0, max(
                    0.0, random.gauss(edge["dependency"], .08)
                ))
                unaffected *= 1.0 - losses[edge["upstream"]] * transmission
            losses[node] = 1.0 - unaffected
        for node in order:
            outcomes[node].append(losses[node])
    ranking = []
    for node in nodes:
        values = sorted(outcomes[node])
        ranking.append({
            "supplier_id": node,
            "mean_exposure": round(mean(values), 5),
            "p95_exposure": round(values[max(0, ceil(.95 * trials) - 1)], 5),
        })
    ranking.sort(key=lambda row: (-row["mean_exposure"], row["supplier_id"]))
    return {
        "disrupted_supplier": supplier_id,
        "severity": severity,
        "trials": trials,
        "seed": seed,
        "source": "tenant_graph",
        "results": ranking,
    }
