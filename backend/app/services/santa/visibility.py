"""
Применение visibility к анкете участника.

Правила:
- каждое поле имеет режим: full / general / hidden;
- full → как есть;
- general → обобщённо (возраст → «30–39», пол → «не указан»);
- hidden → «Участник предпочёл не указывать».

Критично: этот модуль — единственный, кто превращает Participant
в словарь для Санты. Роутеры НЕ должны отдавать ParticipantOut Санте
напрямую — только через apply_visibility().
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from app.models.santa import Participant


# ---------------------------------------------------------------------------
# Поля и их дефолты по политике комнаты
# ---------------------------------------------------------------------------

# Поля, которые можно скрыть (кроме display_name — он всегда виден)
VISIBLE_FIELDS: tuple[str, ...] = (
    "gender",
    "age",
    "interests",
    "antipathies",
    "allergies",
    "constraints",
    "hobbies",
    "brands",
    "sizes",
    "budget_pref_min",
    "budget_pref_max",
)

# Адрес/ПВЗ — не в visibility, а отдельным правилом: виден только Санте
# после жеребьёвки, если заполнен. В visibility не участвует.
PICKUP_FIELD = "pickup_point"


# ---------------------------------------------------------------------------
# Дефолтная visibility по политике комнаты
# ---------------------------------------------------------------------------

def default_visibility(policy: str) -> dict[str, str]:
    """
    open     — все поля full по умолчанию, участник может скрыть;
    balanced — пол/возраст/интересы full, остальное — full, участник может скрыть;
    minimal  — всё general (обобщённо), участник может открыть.

    Во всех политиках участник может ужесточить, но не ослабить ниже политики
    (проверка — в сервисе обновления анкеты).
    """
    if policy == "minimal":
        return {f: "general" for f in VISIBLE_FIELDS}
    # open / balanced — по умолчанию всё видно
    return {f: "full" for f in VISIBLE_FIELDS}


# ---------------------------------------------------------------------------
# Обобщение значений
# ---------------------------------------------------------------------------

def _generalize_age(age: int | None) -> str:
    if age is None:
        return "не указан"
    # 14–17, 18–24, 25–29, 30–39, 40–49, 50–59, 60+
    if age < 18:
        return "14–17"
    if age < 25:
        return "18–24"
    if age < 30:
        return "25–29"
    if age < 40:
        return "30–39"
    if age < 50:
        return "40–49"
    if age < 60:
        return "50–59"
    return "60+"


def _compute_age(p: Participant) -> int | None:
    if p.birth_date is not None:
        today = date.today()
        years = today.year - p.birth_date.year
        if (today.month, today.day) < (p.birth_date.month, p.birth_date.day):
            years -= 1
        return years
    return p.age


# ---------------------------------------------------------------------------
# Применение visibility к одному полю
# ---------------------------------------------------------------------------

def _apply_field(
    field: str,
    value: Any,
    mode: str,
    participant: Participant,
) -> Any:
    if mode == "hidden":
        return "Участник предпочёл не указать"
    if mode == "general":
        if field == "age":
            return _generalize_age(_compute_age(participant))
        if field == "gender":
            return "не указан"
        if field in ("budget_pref_min", "budget_pref_max"):
            return None  # бюджет-предпочтение не обобщаем, просто скрываем
        if field in ("antipathies", "allergies", "constraints", "hobbies", "brands"):
            # свободный текст — обобщить нельзя, показываем факт наличия
            return "Указано" if value else None
        if field == "sizes":
            return "Указано" if value else None
        if field == "interests":
            return value  # интересы по словарю — оставляем как есть
        return value
    # mode == "full"
    return value


# ---------------------------------------------------------------------------
# Главная функция: анкета для Санты
# ---------------------------------------------------------------------------

def apply_visibility(participant: Participant) -> dict[str, Any]:
    """
    Возвращает словарь полей анкеты с учётом visibility.
    Используется в GET assignment/me и в превью.
    """
    vis = participant.visibility or {}
    result: dict[str, Any] = {
        "display_name": participant.display_name,
    }

    for field in VISIBLE_FIELDS:
        mode = vis.get(field, "full")
        value = getattr(participant, field, None)
        # age — вычисляемый, если есть birth_date
        if field == "age":
            value = _compute_age(participant)
        result[field] = _apply_field(field, value, mode, participant)

    return result


# ---------------------------------------------------------------------------
# Превью «как меня видит Санта»
# ---------------------------------------------------------------------------

def build_preview(participant: Participant) -> dict[str, Any]:
    """
    То же, что apply_visibility, плюс предупреждения для участника:
    какие поля скрыты и как это влияет на подборку (FR-2.5, FR-2.7).
    """
    data = apply_visibility(participant)
    warnings: list[str] = []

    vis = participant.visibility or {}
    hidden = [f for f, m in vis.items() if m == "hidden"]
    general = [f for f, m in vis.items() if m == "general"]

    if hidden:
        warnings.append(
            f"Скрыто полей: {len(hidden)}. "
            "Чем больше вы откроете, тем точнее будут идеи для вашего Санты."
        )
    if general:
        warnings.append(
            f"Обобщено полей: {len(general)}. "
            "Обобщённые данные участвуют в подборке частично."
        )
    if not participant.interests:
        warnings.append(
            "Интересы не заполнены — подборка будет универсальной."
        )

    return {"fields": data, "warnings": warnings}


# ---------------------------------------------------------------------------
# Валидация visibility при обновлении анкеты
# ---------------------------------------------------------------------------

def validate_visibility(
    requested: dict[str, str],
    policy: str,
) -> dict[str, str]:
    """
    Проверяет, что участник не ослабляет visibility ниже политики комнаты.
    Возвращает итоговую visibility (мерж с дефолтом по политике).

    Правила:
    - open: можно ужесточить (full → general/hidden);
    - balanced: пол/возраст/интересы нельзя скрыть полностью (только general);
    - minimal: всё по умолчанию general, можно только ужесточить до hidden.
    """
    result = default_visibility(policy)
    for field, mode in requested.items():
        if field not in VISIBLE_FIELDS:
            continue
        if mode not in ("full", "general", "hidden"):
            continue
        result[field] = mode

    # Ограничения по политике
    if policy == "balanced":
        for core_field in ("gender", "age", "interests"):
            if result.get(core_field) == "hidden":
                result[core_field] = "general"

    return result