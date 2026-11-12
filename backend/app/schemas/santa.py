"""
Pydantic-схемы модуля «Тайный Санта».

Контракты API. Все пути — /api/v1/santa/...
Валидация: интересы — по словарю HOBBY/STYLE (проверка в сервисном слое,
здесь — только тип и min_length=1), возраст — birth_date ИЛИ age.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# ENUM-ы (зеркалят БД, для типизации API)
# ---------------------------------------------------------------------------

class RoomStatus(str, Enum):
    draft = "draft"
    collecting = "collecting"
    drawn = "drawn"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"


class VisibilityPolicy(str, Enum):
    open = "open"
    balanced = "balanced"
    minimal = "minimal"


class AnonymityMode(str, Enum):
    full = "full"
    reveal_after = "reveal_after"
    signed = "signed"


class JoinPolicy(str, Enum):
    link = "link"
    code = "code"
    invite = "invite"


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class ParticipantStatus(str, Enum):
    invited = "invited"
    joined = "joined"
    profile_min = "profile_min"
    profile_full = "profile_full"


class DrawStatus(str, Enum):
    generating = "generating"
    ready = "ready"


class GiftStatus(str, Enum):
    pending = "pending"
    chosen = "chosen"
    shipped = "shipped"
    delivered = "delivered"


class SuggestionSource(str, Enum):
    curated = "curated"
    llm = "llm"
    marketplace = "marketplace"


VisibilityMode = Literal["full", "general", "hidden"]


# ---------------------------------------------------------------------------
# Базовые
# ---------------------------------------------------------------------------

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

class RoomCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    event_date: Optional[date] = None
    budget_min: Decimal = Field(..., ge=0)
    budget_max: Decimal = Field(..., ge=0)
    currency: str = Field("RUB", min_length=3, max_length=3)
    tz: str = Field("Europe/Moscow", max_length=64)
    anonymity_mode: AnonymityMode = AnonymityMode.full
    join_policy: JoinPolicy = JoinPolicy.link
    visibility_policy: VisibilityPolicy = VisibilityPolicy.balanced
    max_participants: int = Field(30, ge=3, le=30)
    require_min_profile: bool = True

    @model_validator(mode="after")
    def _check_budget(self) -> "RoomCreate":
        if self.budget_max < self.budget_min:
            raise ValueError("budget_max must be >= budget_min")
        return self


class RoomUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    event_date: Optional[date] = None
    budget_min: Optional[Decimal] = Field(None, ge=0)
    budget_max: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    tz: Optional[str] = Field(None, max_length=64)
    anonymity_mode: Optional[AnonymityMode] = None
    join_policy: Optional[JoinPolicy] = None
    visibility_policy: Optional[VisibilityPolicy] = None
    max_participants: Optional[int] = Field(None, ge=3, le=30)
    require_min_profile: Optional[bool] = None


class RoomOut(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: Optional[str]
    event_date: Optional[date]
    budget_min: Decimal
    budget_max: Decimal
    currency: str
    tz: str
    status: RoomStatus
    anonymity_mode: AnonymityMode
    join_policy: JoinPolicy
    visibility_policy: VisibilityPolicy
    max_participants: int
    require_min_profile: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Participant — анкета
# ---------------------------------------------------------------------------

class PickupPoint(BaseModel):
    """Пункт выдачи вместо полного адреса (3.9)."""
    market: Literal["ozon", "yandex", "other"]
    point_id: Optional[str] = None
    city: Optional[str] = None
    address_hint: Optional[str] = None


class ParticipantPrefillOut(BaseModel):
    """
    Prefill при вступлении: что уже есть в user_profiles, чего не хватает,
    какая visibility предлагается по политике комнаты.
    """
    from_profile: dict[str, Any]
    missing: list[str]
    suggested_visibility: dict[str, VisibilityMode]


class ParticipantCreate(BaseModel):
    """
    Вступление в комнату. Все поля, кроме interests, опциональны —
    если в user_profiles уже есть, досылаются только переопределения.
    Итоговая валидация (interests >= 1, birth_date или age) — в сервисе
    после мержа с source_profile_snapshot.
    """
    display_name: Optional[str] = Field(None, max_length=100)
    gender: Optional[Gender] = None
    birth_date: Optional[date] = None
    age: Optional[int] = Field(None, ge=14, le=120)

    interests: Optional[list[str]] = None
    hobbies: Optional[str] = None
    antipathies: Optional[str] = None
    allergies: Optional[str] = None
    constraints: Optional[str] = None
    brands: Optional[str] = None
    sizes: Optional[dict[str, Any]] = None

    budget_pref_min: Optional[Decimal] = Field(None, ge=0)
    budget_pref_max: Optional[Decimal] = Field(None, ge=0)
    pickup_point: Optional[PickupPoint] = None
    visibility: Optional[dict[str, VisibilityMode]] = None

    @model_validator(mode="after")
    def _check_budget_pref(self) -> "ParticipantCreate":
        if (
            self.budget_pref_min is not None
            and self.budget_pref_max is not None
            and self.budget_pref_max < self.budget_pref_min
        ):
            raise ValueError("budget_pref_max must be >= budget_pref_min")
        return self


class ParticipantUpdate(BaseModel):
    """PATCH /participants/me — частичное обновление, мерж в сервисе."""
    display_name: Optional[str] = Field(None, max_length=100)
    gender: Optional[Gender] = None
    birth_date: Optional[date] = None
    age: Optional[int] = Field(None, ge=14, le=120)
    interests: Optional[list[str]] = None
    hobbies: Optional[str] = None
    antipathies: Optional[str] = None
    allergies: Optional[str] = None
    constraints: Optional[str] = None
    brands: Optional[str] = None
    sizes: Optional[dict[str, Any]] = None
    budget_pref_min: Optional[Decimal] = Field(None, ge=0)
    budget_pref_max: Optional[Decimal] = Field(None, ge=0)
    pickup_point: Optional[PickupPoint] = None
    visibility: Optional[dict[str, VisibilityMode]] = None


class ParticipantOut(ORMModel):
    id: uuid.UUID
    room_id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    gender: Gender
    birth_date: Optional[date]
    age: Optional[int]
    interests: list[str]
    hobbies: Optional[str]
    antipathies: Optional[str]
    allergies: Optional[str]
    constraints: Optional[str]
    brands: Optional[str]
    sizes: Optional[dict[str, Any]]
    budget_pref_min: Optional[Decimal]
    budget_pref_max: Optional[Decimal]
    pickup_point: Optional[dict[str, Any]]
    visibility: dict[str, VisibilityMode]
    profile_completeness: int
    status: ParticipantStatus
    is_deleted: bool
    joined_at: datetime


class ParticipantPublicOut(BaseModel):
    """Список участников: имя + статус анкеты, без анкеты и пар (FR-3.4)."""
    id: uuid.UUID
    display_name: str
    status: ParticipantStatus
    is_deleted: bool


class ParticipantPreviewOut(BaseModel):
    """Превью «как меня видит Санта» с учётом visibility (FR-2.7)."""
    display_name: str
    fields: dict[str, Any]  # поля с учётом visibility: full / general / hidden
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------

class InviteCreate(BaseModel):
    telegram_id: Optional[int] = None
    expires_in_days: int = Field(14, ge=1, le=90)


class InviteOut(ORMModel):
    id: uuid.UUID
    room_id: uuid.UUID
    token: str
    telegram_id: Optional[int]
    expires_at: Optional[datetime]
    used_at: Optional[datetime]
    created_at: datetime
    deep_link: Optional[str] = None  # https://t.me/<bot>?start=join_<token>


# ---------------------------------------------------------------------------
# Exclusion
# ---------------------------------------------------------------------------

class ExclusionCreate(BaseModel):
    participant_a_id: uuid.UUID
    participant_b_id: uuid.UUID

    @model_validator(mode="after")
    def _check_distinct(self) -> "ExclusionCreate":
        if self.participant_a_id == self.participant_b_id:
            raise ValueError("participant_a_id and participant_b_id must differ")
        return self


class ExclusionOut(ORMModel):
    id: uuid.UUID
    room_id: uuid.UUID
    participant_a_id: uuid.UUID
    participant_b_id: uuid.UUID


# ---------------------------------------------------------------------------
# Draw / Assignment
# ---------------------------------------------------------------------------

class DrawCreate(BaseModel):
    """Опции жеребьёвки (FR-4.5: цепочка vs полностью случайная)."""
    mode: Literal["random", "chain"] = "random"


class DrawOut(ORMModel):
    id: uuid.UUID
    room_id: uuid.UUID
    drawn_at: datetime
    drawn_by: Optional[uuid.UUID]
    algorithm_version: str
    status: DrawStatus


class SanteeCardOut(BaseModel):
    """
    Карточка подопечного для Санты (GET assignment/me).
    Анкета — уже с фильтром visibility. Подборка — отдельным эндпоинтом.
    """
    assignment_id: uuid.UUID
    participant: dict[str, Any]  # поля с учётом visibility
    budget_min: Decimal
    budget_max: Decimal
    currency: str
    gift_status: GiftStatus
    viewed_at: Optional[datetime]
    pickup_point: Optional[dict[str, Any]]  # виден только Санте после жеребьёвки
    hints: list[str] = Field(default_factory=list)  # «минимум», «скрыто» и т.п.


class GiftStatusUpdate(BaseModel):
    gift_status: GiftStatus


# ---------------------------------------------------------------------------
# Подборка идей
# ---------------------------------------------------------------------------

class SuggestionItemOut(BaseModel):
    id: uuid.UUID
    external_id: Optional[str]
    idea_title: str
    category: Optional[str]
    tags: list[str]
    price_min: Optional[Decimal]
    price_max: Optional[Decimal]
    reason: Optional[str]
    score: Optional[Decimal]
    source: SuggestionSource


class SuggestionsOut(BaseModel):
    """6 идей на первом запросе, +4 на regenerate (1.3)."""
    assignment_id: uuid.UUID
    generation: int
    items: list[SuggestionItemOut]
    can_regenerate: bool
    regenerations_left: int


class RegenerateOut(SuggestionsOut):
    """Ответ на regenerate: только новые 4 идеи (generation += 1)."""
    added: int


# ---------------------------------------------------------------------------
# Message (анонимный чат пары)
# ---------------------------------------------------------------------------

class MessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class MessageOut(BaseModel):
    """
    from_participant_id наружу НЕ отдаём (анонимизация, 3.4).
    Показываем «от Санты» / «от подопечного».
    """
    id: uuid.UUID
    body: str
    is_revealed: bool
    created_at: datetime
    from_role: Literal["santa", "santee"]


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class NotificationOut(ORMModel):
    id: uuid.UUID
    type: str
    payload: dict[str, Any]
    read_at: Optional[datetime]
    created_at: datetime


# ---------------------------------------------------------------------------
# Dashboard (организатор)
# ---------------------------------------------------------------------------

class DashboardParticipantStat(BaseModel):
    participant_id: uuid.UUID
    display_name: str
    status: ParticipantStatus
    profile_completeness: int
    is_deleted: bool
    gift_status: Optional[GiftStatus] = None  # None, если ещё не жеребьёвка


class DashboardOut(BaseModel):
    room_id: uuid.UUID
    room_status: RoomStatus
    participants_total: int
    participants_profile_min: int
    participants_profile_full: int
    participants_not_filled: int
    draw: Optional[DrawOut]
    participants: list[DashboardParticipantStat]
    # Без подборок и без пар — только агрегаты (FR-5.9, FR-7.3)


# ---------------------------------------------------------------------------
# GDPR export (3.8)
# ---------------------------------------------------------------------------

class ParticipantExportOut(BaseModel):
    participant: ParticipantOut
    source_profile_snapshot: Optional[dict[str, Any]]
    messages_sent: list[MessageOut]
    notifications: list[NotificationOut]