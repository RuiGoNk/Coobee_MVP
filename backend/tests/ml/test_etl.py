"""Проверка, что загрузчик и from_db_item согласованы."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ml.core import category_of, from_db_item
from app.ml.etl import row_to_catalog_fields

FIXTURE = Path(__file__).parent / "fixtures" / "wb_items.jsonl"


def _rows():
    if not FIXTURE.exists():
        pytest.skip("нет фикстуры wb_items.jsonl")
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


def _as_db_item(fields: dict) -> SimpleNamespace:
    base = dict(id=1, image_url=None, marketplace_url=None)
    base.update(fields)
    return SimpleNamespace(**base)


def test_roundtrip_preserves_critical_fields():
    rows = _rows()
    assert rows
    for row in rows:
        fields = row_to_catalog_fields(row)
        rec = from_db_item(_as_db_item(fields))
        assert rec["external_id"] == str(row["sku"])
        assert rec["title"] == row["title"][:256]
        assert rec["price_min"] == (int(round(row["price"]["discounted"]))
                                    if row["price"].get("discounted") else None)
        assert rec["category_path"] == row.get("category_path")
        assert rec["rating"] == row.get("rating")
        assert rec["delivery_days_min"] == (row.get("delivery") or {}).get("days_min")
        assert rec["in_stock"] == (row.get("availability") != "out_of_stock")


def test_category_resolves_for_every_row():
    rows = _rows()
    missing = [r["sku"] for r in rows
               if category_of(from_db_item(_as_db_item(row_to_catalog_fields(r)))) is None]
    assert not missing, f"категория не определилась: {missing[:10]}"