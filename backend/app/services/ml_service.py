"""Сервис рекомендаций: адаптер между БД и ML-пайплайном."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.core import from_db_item, profile_from_recipient, recommend, why_text
from app.ml.retrieval import Index
from app.models.catalog import CatalogItem

logger = logging.getLogger(__name__)

MODEL_VERSION = "rank_v0.6.1+bm25"

_index_cache: dict[str, Any] = {"key": None, "index": None}


def model_version() -> str:
    return MODEL_VERSION


def _index_for(records: list[dict]) -> Index:
    key = (len(records), tuple(r["external_id"] for r in records[:20]))
    if _index_cache["key"] != key:
        _index_cache["key"] = key
        _index_cache["index"] = Index.build(records)
    return _index_cache["index"]


async def recommend_items(user_profile: dict[str, Any],
                          recipient_profile: dict[str, Any],
                          items: list[CatalogItem],
                          limit: int = 5) -> dict:
    """Полный результат: items + reason + model_version. Никогда не бросает."""
    try:
        profile = profile_from_recipient(recipient_profile)
        records = [from_db_item(it) for it in items]
        if not records:
            return {"items": [], "reason": "empty_catalog",
                    "model_version": MODEL_VERSION, "candidates": 0}
        index = _index_for(records)
        result = recommend(profile, records, limit=limit, index=index)
    except Exception:
        logger.exception("ml pipeline failed")
        return {"items": [], "reason": "ml_error",
                "model_version": MODEL_VERSION, "candidates": 0}

    result["model_version"] = MODEL_VERSION
    for entry in result["items"]:
        entry["why"] = why_text(entry.get("why_code"))
    return result


async def get_recommendations(user_profile: dict[str, Any],
                              recipient_profile: dict[str, Any],
                              db: AsyncSession) -> list[str]:
    """Совместимость со старым контрактом: только external_id."""
    stmt = select(CatalogItem).where(CatalogItem.is_available.is_(True))
    items = list((await db.execute(stmt)).scalars().all())
    result = await recommend_items(user_profile, recipient_profile, items)
    return [e["external_id"] for e in result["items"]]