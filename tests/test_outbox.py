import json
from unittest.mock import MagicMock

from nexusgraph import store
from nexusgraph.event_outbox import send_pending


def test_durable_scenario_outbox_delivery(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUSGRAPH_DB_PATH", str(tmp_path / "events.db"))
    store.initialize()
    identifier = store.save_scenario("t1", "tester", {"seed": 7}, {"results": []})
    with store.connect() as db:
        rows = db.execute("SELECT * FROM outbox").fetchall()
    assert len(rows) == 1
    assert json.loads(rows[0]["event_json"])["scenario_id"] == identifier
    producer = MagicMock()

    def deliver(**kwargs):
        kwargs["on_delivery"](None, None)

    producer.produce.side_effect = deliver
    assert send_pending(store, producer=producer) == 1
    assert send_pending(store, producer=producer) == 0
    assert producer.produce.call_count == 1


def test_failure_preserves_pending_event(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUSGRAPH_DB_PATH", str(tmp_path / "events.db"))
    store.initialize()
    store.save_scenario("t1", "tester", {"seed": 7}, {"results": []})
    producer = MagicMock()
    producer.produce.side_effect = lambda **kwargs: kwargs["on_delivery"]("failure", None)
    assert send_pending(store, producer=producer) == 0
    with store.connect() as db:
        pending = db.execute("SELECT count(*) FROM outbox WHERE published_at IS NULL").fetchone()[0]
    assert pending == 1
