from nexusgraph import sqlstore


def test_sqlite_via_sqlalchemy_contract(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "NEXUSGRAPH_DATABASE_URL", "sqlite:///" + str(tmp_path / "data.db")
    )
    sqlstore.initialize()
    assert sqlstore.seed("alpha", "tester") == 10
    assert sqlstore.seed("alpha", "tester") == 0
    assert sqlstore.list_suppliers("beta") == []
    assert len(sqlstore.list_suppliers("alpha")) == 10
    sqlstore.upsert_supplier("alpha", "tester", {
        "id": "CUSTOM", "name": "Test", "region": "US",
        "tier": 1, "capabilities": ["sensors"],
    })
    assert len(sqlstore.list_suppliers("alpha")) == 11
    identifier = sqlstore.save_scenario(
        "alpha", "tester", {"seed": 42}, {"results": []}
    )
    assert sqlstore.list_scenarios("alpha")[0]["id"] == identifier
    assert sqlstore.list_scenarios("beta") == []
    assert len(sqlstore.list_audit("alpha")) >= 3
