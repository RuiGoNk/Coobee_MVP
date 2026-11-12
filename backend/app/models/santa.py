"""
SQLAlchemy-модели модуля «Тайный Санта».

Все таблицы модуля santa. Не пересекаются с recipients/user_profiles:
Participant — это участник комнаты (сам пользователь), а не запись,
которую даритель заводит на другого человека.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ---------------------------------------------------------------------------
# ENUM-типы
# ---------------------------------------------------------------------------

RoomStatus = Enum(
    "draft", "collecting", "drawn", "in_progress", "completed", "archived",
    name="santa_room_status",
)

VisibilityPolicy = Enum(
    "open", "balanced", "minimal",
    name="santa_visibility_policy",
)

AnonymityMode = Enum(
    "full", "reveal_after", "signed",
    name="santa_anonymity_mode",
)

JoinPolicy = Enum(
    "link", "code", "invite",
    name="santa_join_policy",
)

Gender = Enum(
    "male", "female", "other", "prefer_not_to_say",
    name="santa_gender",
)

ParticipantStatus = Enum(
    "invited", "joined", "profile_min", "profile_full",
    name="santa_participant_status",
)

DrawStatus = Enum(
    "generating", "ready",
    name="santa_draw_status",
)

GiftStatus = Enum(
    "pending", "chosen", "shipped", "delivered",
    name="santa_gift_status",
)

SuggestionSource = Enum(
    "curated", "llm", "marketplace",
    name="santa_suggestion_source",
)


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

class Room(Base):
    __tablename__ = "santa_rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    budget_min: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    budget_max: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    tz: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Moscow")

    status: Mapped[str] = mapped_column(RoomStatus, nullable=False, default="draft")
    anonymity_mode: Mapped[str] = mapped_column(
        AnonymityMode, nullable=False, default="full"
    )
    join_policy: Mapped[str] = mapped_column(
        JoinPolicy, nullable=False, default="link"
    )
    visibility_policy: Mapped[str] = mapped_column(
        VisibilityPolicy, nullable=False, default="balanced"
    )
    max_participants: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=30
    )
    require_min_profile: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    exclusions: Mapped[list["Exclusion"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    draws: Mapped[list["Draw"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    invites: Mapped[list["Invite"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("budget_min >= 0", name="ck_santa_room_budget_min"),
        CheckConstraint("budget_max >= budget_min", name="ck_santa_room_budget_range"),
        CheckConstraint(
            "max_participants BETWEEN 3 AND 30",
            name="ck_santa_room_max_participants",
        ),
    )


# ---------------------------------------------------------------------------
# Participant
# ---------------------------------------------------------------------------

class Participant(Base):
    __tablename__ = "santa_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("santa_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    gender: Mapped[str] = mapped_column(Gender, nullable=False)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    age_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    interests: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )
    hobbies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    antipathies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allergies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brands: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sizes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    budget_pref_min: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    budget_pref_max: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    pickup_point: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    visibility: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Снимок user_profiles на момент вступления в комнату.
    # Нужен, чтобы: (1) показать «откуда взялось» поле, (2) не тянуть
    # user_profiles при каждой генерации, (3) зафиксировать значения,
    # если пользователь позже изменит основной профиль.
    source_profile_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )

    profile_completeness: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    status: Mapped[str] = mapped_column(
        ParticipantStatus, nullable=False, default="joined"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    room: Mapped["Room"] = relationship(back_populates="participants")

    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_santa_participant_room_user"),
        CheckConstraint(
            "birth_date IS NOT NULL OR age IS NOT NULL",
            name="ck_santa_participant_age_present",
        ),
        CheckConstraint(
            "age IS NULL OR (age BETWEEN 14 AND 120)",
            name="ck_santa_participant_age_range",
        ),
        CheckConstraint(
            "array_length(interests, 1) >= 1",
            name="ck_santa_participant_interests_min",
        ),
        Index("ix_santa_participants_room", "room_id"),
        Index(
            "ix_santa_participants_interests_gin",
            "interests",
            postgresql_using="gin",
        ),
    )


# ---------------------------------------------------------------------------
# Exclusion
# ---------------------------------------------------------------------------

class Exclusion(Base):
    __tablename__ = "santa_exclusions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("santa_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("santa_participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("santa_participants.id", ondelete="CASCADE"),
        nullable=False,
    )

    room: Mapped["Room"] = relationship(back_populates="exclusions")

    __table_args__ = (
        UniqueConstraint(
            "room_id", "participant_a_id", "participant_b_id",
            name="uq_santa_exclusion_pair",
        ),
        CheckConstraint(
            "participant_a_id <> participant_b_id",
            name="ck_santa_exclusion_distinct",
        ),
    )


# ---------------------------------------------------------------------------
# Draw
# ---------------------------------------------------------------------------

class Draw(Base):
    __tablename__ = "santa_draws"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("santa_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    drawn_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    drawn_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    algorithm_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="v1"
    )
    status: Mapped[str] = mapped_column(
        DrawStatus, nullable=False, default="generating"
    )

    room: Mapped["Room"] = relationship(back_populates="draws")
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="draw", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

class Assignment(Base):
    __tablename__ = "santa_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    draw_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("santa_draws.id", ondelete="CASCADE"),
        nullable=False,
    )
    santa_participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("santa_participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    santee_participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("santa_participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    gift_status: Mapped[str] = mapped_column(
        GiftStatus, nullable=False, default="pending"
    )

    draw: Mapped["Draw"] = relationship(back_populates="assignments")
    suggestions: Mapped[list["GiftSuggestion"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_santa_assignments_santa", "santa_participant_id"),
        CheckConstraint(
            "santa_participant_id IS NULL OR santee_participant_id IS NULL "
            "OR santa_participant_id <> santee_participant_id",
            name="ck_santa_assignment_no_self",
        ),
    )


# ---------------------------------------------------------------------------
# GiftSuggestion
# ---------------------------------------------------------------------------

class GiftSuggestion(Base):
    __tablename__ = "santa_gift_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("santa_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    generation: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    idea_title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    price_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    price_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    source: Mapped[str] = mapped_column(
        SuggestionSource, nullable=False, default="curated"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    assignment: Mapped["Assignment"] = relationship(back_populates="suggestions")

    __table_args__ = (
        Index(
            "ix_santa_suggestions_assignment_gen",
            "assignment_id",
            "generation",
        ),
    )


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class Message(Base):
    __tablename__ = "santa_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("santa_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("santa_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("santa_participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("santa_participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_revealed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_santa_messages_assignment", "assignment_id"),
    )


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class Notification(Base):
    __tablename__ = "santa_notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_santa_notifications_user", "user_id"),
    )


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------

class Invite(Base):
    __tablename__ = "santa_invites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("santa_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    room: Mapped["Room"] = relationship(back_populates="invites")

    __table_args__ = (
        UniqueConstraint("token", name="uq_santa_invite_token"),
    )