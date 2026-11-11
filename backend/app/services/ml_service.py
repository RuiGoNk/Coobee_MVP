from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.catalog import CatalogItem


async def get_recommendations(user_profile: dict[str, Any],
                              recipient_profile: dict[str, Any],
                              db: AsyncSession) -> list[str]:
    """
    Временно: fallback по интересам/бюджету, ровно 5 ID.
    Заменяется на ml.src.harness.pipeline.get_recommendations (импорт или HTTP).
    """
    stmt = select(CatalogItem.id).where(CatalogItem.is_available.is_(True)).limit(5)
    rows = (await db.execute(stmt)).scalars().all()
    return [str(r) for r in rows]