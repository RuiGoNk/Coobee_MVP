"""Загрузка выгрузки парсера в таблицу catalog.

Контракт: поля, которых нет в CatalogItem колонками, кладём в details.
from_db_item() читает только из details — маппинг обязан совпадать.
"""
from __future__ import annotations

from typing import Any


def row_to_catalog_fields(row: dict[str, Any]) -> dict[str, Any]:
    """Строка items.jsonl -> поля CatalogItem (без id/created_at)."""
    price = row.get("price") or {}
    discounted = price.get("discounted")
    regular = price.get("regular")
    price_min = int(round(discounted)) if isinstance(discounted, (int, float)) else None
    price_max = int(round(regular)) if isinstance(regular, (int, float)) else price_min

    images = row.get("images") or []
    category_path = [str(c) for c in (row.get("category_path") or [])]
    identifiers = row.get("identifiers") or {}

    details = {
        "category_path": category_path,
        "subcategory_path": row.get("subcategory_path") or [],
        "attributes": row.get("attributes") or {},
        "rating": row.get("rating"),
        "reviews_count": row.get("reviews_count") or 0,
        "reviews_distribution": row.get("reviews_distribution"),
        "delivery": row.get("delivery") or {},
        "slug": identifiers.get("slug"),
        "brand": row.get("brand"),
        "model": row.get("model"),
        "specs": row.get("specs") or {},
        "badges": row.get("badges") or [],
        "seller": row.get("seller") or {},
        "parsed_at": row.get("parsed_at"),
        "marketplace": row.get("marketplace"),
        "derived": row.get("derived") or {},
    }

    return {
        "external_id": str(row.get("sku")) if row.get("sku") else None,
        "title": (row.get("title") or "")[:256],
        "description": row.get("description") or None,
        "price_min": price_min,
        "price_max": price_max,
        "tags": category_path,
        "image_url": images[0] if images else None,
        "marketplace_url": row.get("url"),
        "is_available": row.get("availability") != "out_of_stock",
        "is_paired": False,
        "delivery_type": "physical",
        "delivery_regions": None,
        "details": details,
    }