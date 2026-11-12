"""
Prefill анкеты участника из user_profiles.

Логика (уточнение по онбордингу):
- если user_profiles заполнен — не заставляем заполнять повторно;
- показываем превью «вот что мы знаем» + «хотите изменить для этой игры?»;
- дозапрашиваем только недостающее (например, pickup_point);
- изменения — только в Participant (user_profiles не трогаем);
- source_profile_snapshot — снимок user_profiles на момент вступления.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tags import HOBBY, STYLE  # словарь тегов (2.3)
from app.models.santa import Participant
from app.models.user import UserProfile
from app.services.santa.visibility import (
    VISIBLE_FIELDS,
    default_visibility,
)


# ---------------------------------------------------------------------------
# Обязательные поля (FR-2.1) — без них нельзя завершить регистрацию
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: tuple[str, ...] = (
    "gender",
    "age",          # birth_date ИЛИ age
    "interests",    # мин. 1, по словарю
)


# ---------------------------------------------------------------------------
# Валидация интересов по словарю
# ---------------------------------------------------------------------------

ALLOWED_INTERESTS: set[str] = set(HOBBY) | set(STYLE)


def validate_interests(interests: list[str]) -> list[str]:
    """
    Оставляет только теги из словаря HOBBY/STYLE.
    Свободный текст — в hobbies (не участвует в генерации в MVP).
    """
    return [i for i in interests if i in ALLOWED_INTERESTS]


def invalid_interests(interests: list[str]) -> list[str]:
    return [i for i in interests if i not in ALLOWED_INTERESTS]


# ---------------------------------------------------------------------------
# Извлечение из user_profiles
# ---------------------------------------------------------------------------

def _profile_to_dict(profile: UserProfile | None) -> dict[str, Any]:
    """
    Приводит user_profiles к словарю полей Participant.
    Возвращает только те поля, которые есть в профиле.
    """
    if profile is None:
        return {}

    result: dict[str, Any] = {}

    if profile.gender:
        result["gender"] = profile.gender

    # возраст: birth_date приоритетнее birth_year
    if profile.birth_date:
        result["birth_date"] = profile.birth_date
    elif profile.birth_year:
        # birth_year → age (точный возраст пересчитывается на лету)
        result["age"] = date.today().year - profile.birth_year

    # интересы — из profile.interests (JSONB), только по словарю
    raw_interests = profile.interests or []
    if isinstance(raw_interests, list):
        valid = validate_interests([str(i) for i in raw_interests])
        if valid:
            result["interests"] = valid

    if profile.city:
        # город — в pickup_point.address_hint (полный адрес не храним, 3.9)
        result.setdefault("pickup_point", {})
        result["pickup_point"]["city"] = profile.city

    # budget_range в user_profiles — enum/строка; для Санты не используем,
    # бюджет задаёт организатор комнаты (2.5). Поле не переносим.
    # (осознанно пропускаем — не пустой if)

    return result


# ---------------------------------------------------------------------------
# Prefill при вступлении
# ---------------------------------------------------------------------------

def build_prefill(
    profile: UserProfile | None,
    visibility_policy: str,
) -> dict[str, Any]:
    """
    Возвращает:
      from_profile   — что уже есть в user_profiles (для превью);
      missing        — каких обязательных полей не хватает;
      suggested_visibility — дефолт по политике комнаты.
    """
    from_profile = _profile_to_dict(profile)

    missing: list[str] = []
    if not from_profile.get("gender"):
        missing.append("gender")
    if not from_profile.get("birth_date") and not from_profile.get("age"):
        missing.append("age")
    if not from_profile.get("interests"):
        missing.append("interests")

    # pickup_point — опционально, но напомним, если пусто
    # (не в missing, чтобы не блокировать)
    return {
        "from_profile": from_profile,
        "missing": missing,
        "suggested_visibility": default_visibility(visibility_policy),
    }


# ---------------------------------------------------------------------------
# Мерж переопределений с source_profile_snapshot
# ---------------------------------------------------------------------------

def merge_with_snapshot(
    snapshot: dict[str, Any] | None,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """
    Мержит переопределения участника со снимком профиля.
    overrides приоритетнее snapshot. None в overrides — не переопределяет
    (partial update).
    """
    result: dict[str, Any] = dict(snapshot or {})
    for key, value in overrides.items():
        if value is not None:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# Финальная валидация после мержа
# ---------------------------------------------------------------------------

def validate_after_merge(merged: dict[str, Any]) -> list[str]:
    """
    Возвращает список недостающих/невалидных полей.
    Пустой список — можно сохранять Participant.
    """
    errors: list[str] = []

    if not merged.get("gender"):
        errors.append("gender")

    if not merged.get("birth_date") and not merged.get("age"):
        errors.append("age")

    interests = merged.get("interests") or []
    valid_interests = validate_interests(interests)
    if not valid_interests:
        errors.append("interests")
    else:
        bad = invalid_interests(interests)
        if bad:
            # не блокируем, но сигнализируем — свободный текст уйдёт в hobbies
            errors.append(f"interests_not_in_dict:{','.join(bad)}")

    # бюджет-предпочтение: если задан min/max — max >= min
    bmin = merged.get("budget_pref_min")
    bmax = merged.get("budget_pref_max")
    if bmin is not None and bmax is not None and bmax < bmin:
        errors.append("budget_pref_range")

    return errors


# ---------------------------------------------------------------------------
# Вычисление profile_completeness (0..100)
# ---------------------------------------------------------------------------

def compute_completeness(data: dict[str, Any]) -> int:
    """
    Доля заполненных полей от VISIBLE_FIELDS + pickup_point.
    Для прогресс-бара (FR-2.3).
    """
    total = len(VISIBLE_FIELDS) + 1  # +1 за pickup_point
    filled = 0

    for field in VISIBLE_FIELDS:
        value = data.get(field)
        if field == "age":
            if data.get("birth_date") or data.get("age"):
                filled += 1
            continue
        if value not in (None, "", [], {}):
            filled += 1

    if data.get("pickup_point"):
        filled += 1

    return int(round(filled / total * 100))