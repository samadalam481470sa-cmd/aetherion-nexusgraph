import pytest

from nexusgraph.ingestion import parse_csv


def test_supplier_csv():
    rows = parse_csv(
        "id,name,region,tier,capabilities\n"
        "SUP-A,Example,US,1,composites;panels\n"
    )
    assert rows[0]["id"] == "SUP-A"
    assert rows[0]["capabilities"] == ["composites", "panels"]


@pytest.mark.parametrize("text", [
    "id,name,region,tier,capabilities\nSUP A,Example,US,1,x\n",
    "id,name,region,tier,capabilities\nSUP-A,Example,US,-1,x\n",
    "id,name,region,tier,capabilities\nSUP-A,Example,US,1,x\nSUP-A,Other,US,2,y\n",
    "name,region,tier,capabilities\nExample,US,1,x\n",
])
def test_rejects_invalid_csv(text):
    with pytest.raises(ValueError):
        parse_csv(text)
