from unittest.mock import MagicMock

import pytest

from nexusgraph.neo4j_projection import project_graph


def test_projection_batches_and_tenant_filtering():
    driver = MagicMock()
    session = driver.session.return_value.__enter__.return_value
    tx = MagicMock()
    session.execute_write.side_effect = lambda callback: callback(tx)
    graph = {
        "suppliers": [{"id": "A", "name": "A", "region": "US", "tier": 1}],
        "dependencies": [],
    }
    result = project_graph(driver, "tenant_one", graph)
    assert result["nodes_projected"] == 1
    assert tx.run.call_count == 4
    for call in tx.run.call_args_list[1:]:
        assert call.kwargs["tenant"] == "tenant_one"


def test_projection_bounds():
    with pytest.raises(ValueError):
        project_graph(None, "", {"suppliers": [], "dependencies": []})
