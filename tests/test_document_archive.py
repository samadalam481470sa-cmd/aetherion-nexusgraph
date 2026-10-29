from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from nexusgraph.document_archive import archive_document, list_documents


def test_document_digest_and_tenant_scope():
    collection = MagicMock()
    result = archive_document(
        collection, "tenantA", "analyst", "SUP-1", "certification",
        {"status": "unverified"},
    )
    assert len(result["sha256"]) == 64
    written = collection.insert_one.call_args.args[0]
    assert written["tenant"] == "tenantA"
    assert written["payload"]["status"] == "unverified"
    collection.find.return_value.sort.return_value.limit.return_value = [{
        "_id": result["id"], "kind": "certification",
        "sha256": result["sha256"],
        "created_at": datetime.now(timezone.utc),
    }]
    rows = list_documents(collection, "tenantB", "SUP-1")
    assert len(rows) == 1
    assert collection.find.call_args.args[0]["tenant"] == "tenantB"


def test_document_size_validation():
    with pytest.raises(ValueError):
        archive_document(MagicMock(), "t", "a", "s", "evidence", {"large": "x" * 40000})
