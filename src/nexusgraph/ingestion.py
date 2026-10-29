"""Bounded, strict CSV supplier import; no external network activity."""
from __future__ import annotations

import csv
import io
import re

from nexusgraph import store

EXPECTED = {"id", "name", "region", "tier", "capabilities"}
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def parse_csv(text: str, maximum: int = 500) -> list[dict]:
    if len(text.encode("utf-8")) > 256_000:
        raise ValueError("CSV exceeds 256 KB")
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if reader.fieldnames is None or set(reader.fieldnames) != EXPECTED:
            raise ValueError("CSV fields must be id,name,region,tier,capabilities")
        rows: list[dict] = []
        ids: set[str] = set()
        for record in reader:
            if len(rows) >= maximum:
                raise ValueError("Too many supplier rows")
            identifier = record["id"]
            name = record["name"]
            region = record["region"]
            if not identifier or not IDENTIFIER.fullmatch(identifier):
                raise ValueError("Invalid supplier ID")
            if identifier in ids:
                raise ValueError("Duplicate supplier ID")
            ids.add(identifier)
            if not name or len(name) > 200 or not region or len(region) > 32:
                raise ValueError("Invalid name or region")
            try:
                tier = int(record["tier"])
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid tier") from exc
            if not 0 <= tier <= 20:
                raise ValueError("Tier out of range")
            capabilities = [value.strip() for value in record["capabilities"].split(";")]
            capabilities = [value for value in capabilities if value]
            if len(capabilities) > 30 or any(len(v) > 64 for v in capabilities):
                raise ValueError("Invalid capabilities")
            rows.append({
                "id": identifier, "name": name, "region": region,
                "tier": tier, "capabilities": capabilities,
            })
        return rows
    except (csv.Error, TypeError, AttributeError) as exc:
        raise ValueError("Malformed supplier CSV") from exc


def import_suppliers(tenant: str, actor: str, csv_text: str) -> int:
    rows = parse_csv(csv_text)
    store.initialize()
    for supplier in rows:
        store.upsert_supplier(tenant, actor, supplier)
    return len(rows)
