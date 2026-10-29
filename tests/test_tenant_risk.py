from nexusgraph.tenant_risk import simulate_graph


def test_simulation_uses_only_tenant_owned_graph():
    graph = {
        "suppliers": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "dependencies": [
            {"upstream": "A", "downstream": "B", "dependency": .75},
            {"upstream": "B", "downstream": "C", "dependency": .5},
        ],
    }
    results = simulate_graph(graph, "A", .8, 250, 42)
    assert results == simulate_graph(graph, "A", .8, 250, 42)
    scores = {row["supplier_id"]: row["mean_exposure"] for row in results["results"]}
    assert scores["A"] == .8
    assert scores["B"] > scores["C"] > 0
    assert results["source"] == "tenant_graph"
