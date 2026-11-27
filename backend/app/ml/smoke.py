"""Смоук-проверка пайплайна на данных из БД.

Запуск:  python -m app.ml.smoke
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.catalog import CatalogItem
from app.services.ml_service import recommend_items

RECIPIENTS = [
    {"name": "маме 58, ДР", "relationship": "mother", "occasion": "birthday",
     "gender": "female", "age": 58, "budget_range": "standard",
     "details": {"interests": ["cooking", "gardening"]}},
    {"name": "другу 27, НГ, symbolic", "relationship": "friend_m",
     "occasion": "new_year", "gender": "male", "age": 27,
     "budget_range": "symbolic", "details": {}},
    {"name": "ребёнку 3 года", "relationship": "child", "occasion": "birthday",
     "gender": "unisex", "age": 3, "budget_range": "symbolic",
     "details": {"interests": []}},
    {"name": "коллеге 40, 8 марта", "relationship": "colleague", "occasion": "mar8",
     "gender": "female", "age": 40, "budget_range": "standard", "details": {}},
    {"name": "жене 30, годовщина, solid", "relationship": "wife",
     "occasion": "anniversary", "gender": "female", "age": 30,
     "budget_range": "solid", "details": {"interests": ["beauty"]}},
]


async def main() -> None:
    async with SessionLocal() as db:
        items = list((await db.execute(select(CatalogItem))).scalars().all())
    print(f"товаров в каталоге: {len(items)}\n")

    for recipient in RECIPIENTS:
        out = await recommend_items({}, recipient, items)
        print(f"== {recipient['name']}")
        print(f"   версия {out['model_version']} | кандидатов {out.get('candidates')} "
              f"| шаг бюджета x{out.get('budget_step')}")
        if not out["items"]:
            print(f"   пусто: {out.get('reason')}")
        for e in out["items"]:
            print(f"   {e['position']}. {str(e['title'])[:48]:50} "
                  f"{e['price'] or 0:>6.0f}₽ {str(e['category']):<17} "
                  f"{e['score']:.3f} | {e.get('why')}")
        print()


if __name__ == "__main__":
    asyncio.run(main())