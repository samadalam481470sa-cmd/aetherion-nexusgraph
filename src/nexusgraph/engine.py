"""Deterministic, interpretable dependency propagation on a synthetic supply graph."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import ceil
from random import Random
from statistics import mean


@dataclass(frozen=True)
class Supplier:
    id: str
    name: str
    region: str
    capabilities: tuple[str, ...]
    tier: int


@dataclass(frozen=True)
class Dependency:
    upstream: str
    downstream: str
    dependency: float
    part: str

    def __post_init__(self) -> None:
        if not (0 <= self.dependency <= 1):
            raise ValueError("Dependency must be between zero and one")


SUPPLIERS = (
    Supplier("SUP-001", "Aetherion Airframe Assembly", "US", ("airframe",), 0),
    Supplier("SUP-002", "Cobalt Composite Works", "US", ("composites", "panels"), 1),
    Supplier("SUP-003", "Northern Actuator Systems", "CA", ("actuators",), 1),
    Supplier("SUP-004", "Solstice Resin Labs", "US", ("resin",), 2),
    Supplier("SUP-005", "Meridian Precision Metals", "MX", ("titanium",), 2),
    Supplier("SUP-006", "Polaris Carbon Materials", "DE", ("carbon_fiber",), 2),
    Supplier("SUP-007", "Atlas Composite Alternatives", "US", ("composites", "panels"), 1),
    Supplier("SUP-008", "Vertex Motion Devices", "US", ("actuators",), 1),
    Supplier("SUP-009", "Cascade Sensorics", "US", ("sensors",), 2),
    Supplier("SUP-010", "Horizon Avionics Integration", "US", ("avionics",), 1),
)
DEPENDENCIES = (
    Dependency("SUP-002", "SUP-001", .70, "composite panel"),
    Dependency("SUP-003", "SUP-001", .50, "actuator"),
    Dependency("SUP-010", "SUP-001", .35, "avionics"),
    Dependency("SUP-004", "SUP-002", .65, "resin"),
    Dependency("SUP-006", "SUP-002", .75, "carbon fiber"),
    Dependency("SUP-005", "SUP-003", .55, "machined titanium"),
    Dependency("SUP-009", "SUP-003", .40, "position sensor"),
    Dependency("SUP-009", "SUP-010", .60, "sensor assembly"),
    Dependency("SUP-004", "SUP-007", .45, "resin"),
    Dependency("SUP-005", "SUP-008", .65, "machined titanium"),
)


def validate_network(suppliers=SUPPLIERS, edges=DEPENDENCIES) -> None:
    ids = [s.id for s in suppliers]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate supplier identifier")
    known = set(ids)
    children = defaultdict(list)
    indegree = {key: 0 for key in known}
    for edge in edges:
        if edge.upstream not in known or edge.downstream not in known:
            raise ValueError("Edge references unknown supplier")
        if edge.upstream == edge.downstream:
            raise ValueError("Self-dependency is not allowed")
        children[edge.upstream].append(edge.downstream)
        indegree[edge.downstream] += 1
    queue = deque(key for key, n in indegree.items() if n == 0)
    visited = 0
    while queue:
        parent = queue.popleft()
        visited += 1
        for child in children[parent]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if visited != len(known):
        raise ValueError("Cyclic graph not supported by this propagation model")


def topological_order(suppliers=SUPPLIERS, edges=DEPENDENCIES) -> list[str]:
    validate_network(suppliers, edges)
    indegree = {s.id: 0 for s in suppliers}
    out = defaultdict(list)
    for edge in edges:
        indegree[edge.downstream] += 1
        out[edge.upstream].append(edge.downstream)
    ready = deque(sorted(s for s, n in indegree.items() if n == 0))
    order = []
    while ready:
        node = ready.popleft()
        order.append(node)
        for nxt in sorted(out[node]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
    return order


def simulate(disrupted_supplier: str, severity: float, trials: int = 500, seed: int = 42) -> dict:
    """Sample edge transmission variability; combine multiple impacts as independent exposures."""
    known = {s.id for s in SUPPLIERS}
    if disrupted_supplier not in known:
        raise ValueError("Unknown supplier ID")
    if not 0 <= severity <= 1:
        raise ValueError("Severity must be in [0, 1]")
    if not 1 <= trials <= 10000:
        raise ValueError("Trials must be between 1 and 10000")
    rng = Random(seed)
    incoming = defaultdict(list)
    for edge in DEPENDENCIES:
        incoming[edge.downstream].append(edge)
    order = topological_order()
    samples = {node: [] for node in order}
    for _ in range(trials):
        loss = {node: 0.0 for node in order}
        loss[disrupted_supplier] = severity
        for node in order:
            if node == disrupted_supplier:
                continue
            survival = 1.0
            for edge in incoming[node]:
                transfer = min(1.0, max(0.0, rng.gauss(edge.dependency, .08)))
                survival *= 1.0 - loss[edge.upstream] * transfer
            loss[node] = 1.0 - survival
        for node in order:
            samples[node].append(loss[node])
    results = []
    for node in order:
        values = sorted(samples[node])
        results.append({
            "supplier_id": node,
            "mean_exposure": round(mean(values), 5),
            "p95_exposure": round(values[max(0, ceil(.95 * trials) - 1)], 5),
        })
    results.sort(key=lambda item: (-item["mean_exposure"], item["supplier_id"]))
    return {"disrupted_supplier": disrupted_supplier, "severity": severity,
            "trials": trials, "seed": seed, "results": results}


def criticality() -> list[dict]:
    """Sum downstream weighted path influences, taking max influence per unique destination."""
    outgoing = defaultdict(list)
    for edge in DEPENDENCIES:
        outgoing[edge.upstream].append(edge)
    order = topological_order()
    scores = []
    for source in order:
        best = {source: 1.0}
        for node in order:
            for edge in outgoing[node]:
                candidate = best.get(node, 0.0) * edge.dependency
                best[edge.downstream] = max(best.get(edge.downstream, 0.0), candidate)
        score = sum(v for node, v in best.items() if node != source)
        scores.append({"supplier_id": source, "downstream_influence": round(score, 5),
                       "reachable_buyers": len(best) - 1})
    return sorted(scores, key=lambda row: (-row["downstream_influence"], row["supplier_id"]))


def alternatives(supplier_id: str) -> list[dict]:
    by_id = {s.id: s for s in SUPPLIERS}
    if supplier_id not in by_id:
        raise ValueError("Unknown supplier ID")
    source = by_id[supplier_id]
    return [{"supplier_id": candidate.id, "name": candidate.name,
             "shared_capabilities": sorted(set(source.capabilities) & set(candidate.capabilities)),
             "qualification_status": "NOT_VERIFIED"}
            for candidate in SUPPLIERS
            if candidate.id != supplier_id and set(source.capabilities) & set(candidate.capabilities)]


validate_network()
