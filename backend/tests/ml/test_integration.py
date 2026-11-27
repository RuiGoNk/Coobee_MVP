from types import SimpleNamespace

import pytest

from app.services.ml_service import MODEL_VERSION, recommend_items


def item(**kw):
    base = dict(id=1, external_id="e1", title="Подарочный набор",
                description="", price_min=2000, price_max=2000,
                is_available=True, tags=[], details={},
                image_url=None, marketplace_url=None)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_recommend_items_returns_five_in_budget():
    items = [
        item(id=1, external_id="a", title="Чайный сервиз", price_min=3000,
             details={"category_path": ["Посуда и инвентарь"]}),
        item(id=2, external_id="b", title="Торшер", price_min=2500,
             details={"category_path": ["Освещение"]}),
        item(id=3, external_id="c", title="Крем для рук", price_min=1500,
             details={"category_path": ["Красота"]}),
        item(id=4, external_id="d", title="Плед шерстяной", price_min=4000,
             details={"category_path": ["Текстиль для дома"]}),
        item(id=5, external_id="e", title="Термокружка", price_min=1200,
             details={"category_path": ["Посуда и инвентарь"]}),
        item(id=6, external_id="f", title="Дорогой сервиз", price_min=49000,
             details={"category_path": ["Посуда и инвентарь"]}),
    ]
    recipient = {"relationship": "mother", "occasion": "birthday",
                 "gender": "female", "age": 58, "budget_range": "standard",
                 "details": {"interests": ["cooking"]}}
    out = await recommend_items({}, recipient, items)

    assert out["model_version"] == MODEL_VERSION
    ids = [e["external_id"] for e in out["items"]]
    assert len(ids) == 5
    assert "f" not in ids                     # вне бюджета
    assert all(e["why"] for e in out["items"])


@pytest.mark.asyncio
async def test_ml_failure_degrades_without_raising():
    broken = SimpleNamespace(id=1, external_id="x", title="Товар",
                             price_min=1000, price_max=1000, is_available=True,
                             tags=[], description="")   # нет .details
    out = await recommend_items({}, {"budget_range": "standard"}, [broken])
    assert out["reason"] in {"ml_error", "empty_catalog"}
    assert out["items"] == []
