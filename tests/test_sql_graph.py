import pytest

from nexusgraph import sql_graph, sqlstore


@pytest.fixture()
def graph_database(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "NEXUSGRAPH_DATABASE_URL", "sqlite:///" + str(tmp_path / "test.db")
    )
    sqlstore.initialize()
    sql_graph.initialize_edges()


def test_sql_graph_persistence_and_cycle_guard(graph_database):
    for key in ("A", "B", "C"):
        sqlstore.upsert_supplier("t1", "actor", {
            "id": key, "name": key, "region": "US",
            "tier": 1, "capabilities": ["test"],
        })
    sql_graph.upsert_edge("t1", "actor", {
        "upstream": "A", "downstream": "B", "part": "p", "dependency": .8,
    })
    sql_graph.upsert_edge("t1", "actor", {
        "upstream": "B", "downstream": "C", "part": "p", "dependency": .6,
    })
    with pytest.raises(ValueError, match="cycle"):
        sql_graph.upsert_edge("t1", "actor", {
            "upstream": "C", "downstream": "A", "part": "p", "dependency": .5,
        })
    assert len(sql_graph.graph("t1")["dependencies"]) == 2
    assert sql_graph.graph("t2")["dependencies"] == []
    scores = sql_graph.criticality_for_tenant("t1")
    assert scores[0]["supplier_id"] == "A"
