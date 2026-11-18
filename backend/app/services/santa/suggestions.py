"""
Генерация подборки идей из catalog (10 товаров, 1.4).

Правила:
- 6 идей на первом запросе, +4 на regenerate (1.3);
- лимит 10 перегенераций на пару (FR-5.6);
- фильтры: бюджет комнаты (стремимся к budget_max, 2.5),
  антипатии/аллергии/constraints, возраст (FR-5.5);
- учитываем visibility: скрытые поля не участвуют, обобщённые — частично
  (FR-5.8);
- reason — обоснование для пары (FR-5.3);
- ML пока нет — source='curated' (1.4).
"""

from __future__ import annotations

import random
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tags import HOBBY, STYLE
from app.models.catalog import CatalogItem
from app.models.santa import Assignment, GiftSuggestion, Participant
from app.services.santa.visibility import apply_visibility


FIRST_BATCH = 6       # 1.3
REGEN_BATCH = 4       # 1.3
MAX_REGENERATIONS = 10  # FR-5.6


# ---------------------------------------------------------------------------
# Возраст участника
# ---------------------------------------------------------------------------

def _effective_age(p: Participant) -> int | None:
    if p.birth_date is not None:
        today = date.today()
        years = today.year - p.birth_date.year
        if (today.month, today.day) < (p.birth_date.month, p.birth_date.day):
            years -= 1
        return years
    return p.age


# ---------------------------------------------------------------------------
# Стоп-слова из анкеты (антипатии / аллергии / constraints)
# ---------------------------------------------------------------------------

def _extract_stopwords(santee: Participant) -> set[str]:
    """
    Простая эвристика: приводим тексты к нижнему регистру, разбиваем
    по запятым/пробелам, оставляем слова длиной >= 3.
    Используется для отсева идей по title/description/tags.
    """
    text_parts: list[str] = []
    for field in ("antipathies", "allergies", "constraints"):
        value = getattr(santee, field, None)
        if value:
            text_parts.append(str(value).lower())

    if not text_parts:
        return set()

    raw = " ".join(text_parts).replace(",", " ").replace(";", " ")
    return {w for w in raw.split() if len(w) >= 3}


def _idea_contains_stopword(idea: CatalogItem, stopwords: set[str]) -> bool:
    if not stopwords:
        return False
    haystack_parts = [
        str(idea.title or ""),
        str(idea.description or ""),
    ]
    tags = idea.tags or []
    if isinstance(tags, list):
        haystack_parts.extend(str(t) for t in tags)
    haystack = " ".join(haystack_parts).lower()
    return any(w in haystack for w in stopwords)


# ---------------------------------------------------------------------------
# Фильтры каталога
# ---------------------------------------------------------------------------

def _in_budget(idea: CatalogItem, budget_min: Decimal, budget_max: Decimal) -> bool:
    """Пересечение [price_min, price_max] товара с бюджетом комнаты."""
    pmin_raw = idea.price_min if idea.price_min is not None else Decimal("0")
    pmax_raw = idea.price_max if idea.price_max is not None else pmin_raw
    pmin = Decimal(str(pmin_raw))
    pmax = Decimal(str(pmax_raw))
    bmin = Decimal(str(budget_min))
    bmax = Decimal(str(budget_max))
    # хотя бы частичное пересечение
    return not (pmax < bmin or pmin > bmax)


def _matches_interests(idea: CatalogItem, interests: list[str]) -> bool:
    if not interests:
        return False
    tags = idea.tags or []
    if not isinstance(tags, list):
        return False
    return bool(set(str(t) for t in tags) & set(interests))


def _age_ok(idea: CatalogItem, age: int | None) -> bool:
    if age is None:
        return True
    details = idea.details or {}
    # age_groups в details: список строк вида "18-24", "25-34" и т.п.
    groups = details.get("age_groups") if isinstance(details, dict) else None
    if not groups:
        return True
    # простая проверка: попадает ли возраст в какой-либо диапазон
    for g in groups:
        try:
            lo, hi = str(g).split("-")
            if int(lo) <= age <= int(hi):
                return True
        except (ValueError, AttributeError):
            continue
    # если группы заданы, но не распарсились — не отсекаем (безопаснее)
    return True


# ---------------------------------------------------------------------------
# Скоринг
# ---------------------------------------------------------------------------

def _score(
    idea: CatalogItem,
    interests: list[str],
    budget_min: Decimal,
    budget_max: Decimal,
) -> float:
    """
    score = совпадение интересов + бонус за близость к budget_max (2.5).
    Возвращает float 0..~2.
    """
    # интерес
    tags = idea.tags or []
    tags_set = set(str(t) for t in tags) if isinstance(tags, list) else set()
    interest_hits = len(tags_set & set(interests))
    interest_score = min(interest_hits / max(len(interests), 1), 1.0)

    # бюджет: чем ближе price_max к budget_max, тем выше
    # catalog.price_min/max могут быть float (SQLAlchemy), а budget_min/max —
    # Decimal (Room). Приводим всё к Decimal через str, чтобы не ловить
    # TypeError: unsupported operand type(s) for -: 'float' and 'Decimal'.
    pmin_raw = idea.price_min if idea.price_min is not None else Decimal("0")
    pmax_raw = idea.price_max if idea.price_max is not None else pmin_raw
    pmin = Decimal(str(pmin_raw))
    pmax = Decimal(str(pmax_raw))
    mid = (pmin + pmax) / Decimal("2")

    bmin = Decimal(str(budget_min))
    bmax = Decimal(str(budget_max))
    span = bmax - bmin
    if span <= 0:
        budget_score = 1.0
    else:
        # ближе к максимуму → 1, ближе к минимуму → 0
        ratio = (mid - bmin) / span
        budget_score = max(0.0, min(1.0, float(ratio)))

    return interest_score + budget_score


# ---------------------------------------------------------------------------
# Обоснование (reason)
# ---------------------------------------------------------------------------

def _reason(
    idea: CatalogItem,
    interests: list[str],
    general: bool,
) -> str:
    tags = idea.tags or []
    tags_set = set(str(t) for t in tags) if isinstance(tags, list) else set()
    hits = tags_set & set(interests)

    if general:
        return "Универсальная идея в рамках бюджета (детали анкеты скрыты)"

    if hits:
        return f"почему: интерес «{', '.join(sorted(hits))}»"
    return "почему: подходит по бюджету и возрасту"


# ---------------------------------------------------------------------------
# Выборка идей
# ---------------------------------------------------------------------------

async def _load_catalog(db: AsyncSession) -> list[CatalogItem]:
    stmt = select(CatalogItem).where(CatalogItem.is_available.is_(True))
    return list((await db.execute(stmt)).scalars().all())


def _pick(
    catalog: list[CatalogItem],
    santee: Participant,
    budget_min: Decimal,
    budget_max: Decimal,
    n: int,
    exclude_ids: set[str],
    rng: random.Random,
) -> list[tuple[CatalogItem, float, str]]:
    """
    Возвращает список (идея, score, reason) длиной до n.
    exclude_ids — external_id уже показанных идей (для regenerate).
    """
    visible = apply_visibility(santee)
    interests = visible.get("interests") or []
    general = visible.get("gender") == "не указан" and visible.get("age") in (
        "не указан", "Участник предпочёл не указать"
    )

    age = _effective_age(santee)
    stopwords = _extract_stopwords(santee)

    candidates: list[tuple[CatalogItem, float, str]] = []

    for idea in catalog:
        ext = getattr(idea, "external_id", None)
        if ext and ext in exclude_ids:
            continue
        if not _in_budget(idea, budget_min, budget_max):
            continue
        if not _age_ok(idea, age):
            continue
        if _idea_contains_stopword(idea, stopwords):
            continue

        # при скрытых интересах не отсекаем по интересам — только универсальные
        if interests and not _matches_interests(idea, interests):
            # не отсекаем полностью, но score будет ниже
            pass

        score = _score(idea, interests, budget_min, budget_max)
        reason = _reason(idea, interests, general=general and not interests)
        candidates.append((idea, score, reason))

    # сортировка по score desc, затем случайный tiebreak для вариативности
    candidates.sort(key=lambda x: (-x[1], rng.random()))

    return candidates[:n]


# ---------------------------------------------------------------------------
# Сохранение подборки
# ---------------------------------------------------------------------------

async def generate_first_batch(
    db: AsyncSession,
    assignment: Assignment,
    budget_min: Decimal,
    budget_max: Decimal,
    seed: int | None = None,
) -> list[GiftSuggestion]:
    """
    Первая подборка (6 идей, generation=0). Вызывается из Celery после draw.
    """
    santee = await db.get(Participant, assignment.santee_participant_id)
    if santee is None:
        return []

    catalog = await _load_catalog(db)
    rng = random.Random(seed) if seed is not None else random.Random()

    picked = _pick(
        catalog, santee, budget_min, budget_max,
        n=FIRST_BATCH, exclude_ids=set(), rng=rng,
    )

    saved: list[GiftSuggestion] = []
    for idea, score, reason in picked:
        sug = GiftSuggestion(
            assignment_id=assignment.id,
            generation=0,
            external_id=getattr(idea, "external_id", None),
            idea_title=idea.title,
            category=(idea.details or {}).get("category") if isinstance(idea.details, dict) else None,
            tags=list(idea.tags or []) if isinstance(idea.tags, list) else [],
            price_min=idea.price_min,
            price_max=idea.price_max,
            reason=reason,
            score=Decimal(str(round(score, 4))),
            source="curated",
        )
        db.add(sug)
        saved.append(sug)

    await db.flush()
    return saved


async def regenerate(
    db: AsyncSession,
    assignment: Assignment,
    budget_min: Decimal,
    budget_max: Decimal,
    seed: int | None = None,
) -> list[GiftSuggestion]:
    """
    +4 новые идеи (generation += 1). Исключает уже показанные external_id.
    Лимит перегенераций проверяется в роутере (FR-5.6).
    """
    santee = await db.get(Participant, assignment.santee_participant_id)
    if santee is None:
        return []

    # текущая максимальная generation
    stmt = select(GiftSuggestion).where(GiftSuggestion.assignment_id == assignment.id)
    existing = list((await db.execute(stmt)).scalars().all())

    if not existing:
        # ещё не было первой генерации — считаем это первой
        return await generate_first_batch(
            db, assignment, budget_min, budget_max, seed=seed
        )

    current_gen = max(s.generation for s in existing)
    next_gen = current_gen + 1
    exclude_ids = {s.external_id for s in existing if s.external_id}

    catalog = await _load_catalog(db)
    rng = random.Random(seed) if seed is not None else random.Random()

    picked = _pick(
        catalog, santee, budget_min, budget_max,
        n=REGEN_BATCH, exclude_ids=exclude_ids, rng=rng,
    )

    saved: list[GiftSuggestion] = []
    for idea, score, reason in picked:
        sug = GiftSuggestion(
            assignment_id=assignment.id,
            generation=next_gen,
            external_id=getattr(idea, "external_id", None),
            idea_title=idea.title,
            category=(idea.details or {}).get("category") if isinstance(idea.details, dict) else None,
            tags=list(idea.tags or []) if isinstance(idea.tags, list) else [],
            price_min=idea.price_min,
            price_max=idea.price_max,
            reason=reason,
            score=Decimal(str(round(score, 4))),
            source="curated",
        )
        db.add(sug)
        saved.append(sug)

    await db.flush()
    return saved


# ---------------------------------------------------------------------------
# Подсчёт для лимита
# ---------------------------------------------------------------------------

async def regenerations_used(db: AsyncSession, assignment_id: uuid.UUID) -> int:
    """
    Сколько раз уже перегенерировали (generation > 0 → count уникальных gen).
    """
    stmt = select(GiftSuggestion.generation).where(
        GiftSuggestion.assignment_id == assignment_id,
        GiftSuggestion.generation > 0,
    )
    gens = {row for row in (await db.execute(stmt)).scalars().all()}
    return len(gens)