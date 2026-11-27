"""Загрузка выгрузки парсера в таблицу catalog.

Запуск внутри контейнера:
    python -m app.ml.seed_catalog /app/out/items.jsonl
Повторный запуск обновляет записи по external_id (upsert).
"""
from __future__ import annotations

import asyncio
import json
import sys

from sqlalchemy import select

from app.db.session import SessionLocal
from app.ml.etl import row_to_catalog_fields
from app.models.catalog import CatalogItem


async def seed(path: str, replace: bool = False) -> None:
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    print(f"строк в файле: {len(rows)}")

    async with SessionLocal() as db:
        if replace:
            existing = (await db.execute(select(CatalogItem))).scalars().all()
            for it in existing:
                await db.delete(it)
            await db.commit()
            print(f"удалено старых записей: {len(existing)}")

        created = updated = skipped = 0
        for row in rows:
            ext = str(row.get("sku") or "").strip()
            if not ext:
                skipped += 1
                continue
            fields = row_to_catalog_fields(row)
            found = (await db.execute(
                select(CatalogItem).where(CatalogItem.external_id == ext)
            )).scalar_one_or_none()

            if found is None:
                db.add(CatalogItem(**fields))
                created += 1
            else:
                for k, v in fields.items():
                    setattr(found, k, v)
                updated += 1

        await db.commit()
        total = (await db.execute(select(CatalogItem))).scalars().all()
        print(f"создано {created}, обновлено {updated}, пропущено {skipped}")
        print(f"всего в catalog: {len(total)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m app.ml.seed_catalog <items.jsonl> [--replace]")
        raise SystemExit(2)
    asyncio.run(seed(sys.argv[1], "--replace" in sys.argv[2:]))