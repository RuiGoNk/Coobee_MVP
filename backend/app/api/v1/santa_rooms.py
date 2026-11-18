"""
Роутер модуля santa: комнаты, участники, приглашения.

Пути (под /api/v1/santa):
- POST   /rooms                       — создать комнату
- GET    /rooms/{id}                  — инфо о комнате (участник)
- PATCH  /rooms/{id}                  — настройки (организатор, до draw)
- POST   /rooms/{id}/invite           — приглашение (организатор)
- GET    /rooms/{id}/participants     — список (имя+статус, без анкет/пар)
- GET    /rooms/{id}/participants/me/prefill  — prefill из user_profiles
- PATCH  /rooms/{id}/participants/me  — анкета + visibility
- GET    /rooms/{id}/participants/me/preview  — «как меня видит Санта»
- POST   /join/{token}                — вступить по токену
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.santa import Exclusion, Invite, Participant, Room
from app.models.user import User, UserProfile
from app.schemas.santa import (
    ExclusionCreate,
    ExclusionOut,
    InviteCreate,
    InviteOut,
    ParticipantCreate,
    ParticipantOut,
    ParticipantPrefillOut,
    ParticipantPreviewOut,
    ParticipantPublicOut,
    ParticipantUpdate,
    RoomCreate,
    RoomOut,
    RoomUpdate,
)
from app.services.santa import notifications as notif
from app.services.santa.access import (
    ensure_room_editable,
    get_current_organizer,
    get_current_participant,
    get_room_or_404,
)
from app.services.santa.prefill import (
    build_prefill,
    compute_completeness,
    merge_with_snapshot,
    normalize_birth_date,   # ← добавь
    validate_after_merge,
)
from app.services.santa.visibility import (
    build_preview,
    validate_visibility,
)


router = APIRouter(prefix="/rooms", tags=["santa: rooms"])


# ---------------------------------------------------------------------------
# Создание комнаты
# ---------------------------------------------------------------------------

@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Room:
    room = Room(
        owner_id=user.id,
        title=payload.title,
        description=payload.description,
        event_date=payload.event_date,
        budget_min=payload.budget_min,
        budget_max=payload.budget_max,
        currency=payload.currency,
        tz=payload.tz,
        anonymity_mode=payload.anonymity_mode.value,
        join_policy=payload.join_policy.value,
        visibility_policy=payload.visibility_policy.value,
        max_participants=payload.max_participants,
        require_min_profile=payload.require_min_profile,
        status="collecting",
    )
    db.add(room)
    await db.flush()

    # Организатор автоматически становится участником:
    # он тоже дарит и получает подарок. Анкету заполнит отдельно
    # (prefill / PATCH participants/me), пока — минимальная заглушка.
    organizer_profile_stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    organizer_profile = (await db.execute(organizer_profile_stmt)).scalar_one_or_none()
    snapshot = build_prefill(organizer_profile, room.visibility_policy)["from_profile"]

    # Если в профиле есть gender/age/interests — используем; иначе заглушка,
    # чтобы participant существовал (анкету можно дозаполнить позже).
    from datetime import date as _date

    gender = snapshot.get("gender") or "prefer_not_to_say"

    # snapshot["birth_date"] — ISO-строка (JSONB), парсим обратно в date
    birth_date_raw = snapshot.get("birth_date")
    if isinstance(birth_date_raw, str):
        try:
            birth_date = _date.fromisoformat(birth_date_raw)
        except ValueError:
            birth_date = None
    else:
        birth_date = birth_date_raw  # если уже date (на случай других путей)

    age = snapshot.get("age")
    if birth_date is None and age is None:
        age = 10  # минимальный валидный возраст, пока не заполнит
    interests = snapshot.get("interests") or ["tech"]  # мин. 1 по CHECK

    organizer_participant = Participant(
        room_id=room.id,
        user_id=user.id,
        display_name=user.username or "Организатор",
        gender=gender,
        birth_date=birth_date,
        age=age,
        interests=interests,
        visibility=validate_visibility({}, room.visibility_policy),
        source_profile_snapshot=snapshot,
        profile_completeness=compute_completeness(snapshot),
        status="joined",
    )
    db.add(organizer_participant)

    await db.commit()
    await db.refresh(room)
    return room
# ---------------------------------------------------------------------------
# Мои комнаты (где я owner или участник)
# ---------------------------------------------------------------------------

@router.get("/my", response_model=list[RoomOut])
async def list_my_rooms(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Room]:
    """
    Все комнаты, где текущий пользователь — организатор (owner_id)
    или участник (Participant.user_id).

    ВАЖНО: объявлен ДО /{room_id}, иначе FastAPI парсит "my" как UUID.
    """
    owned_stmt = select(Room.id).where(Room.owner_id == user.id)
    owned_ids = set((await db.execute(owned_stmt)).scalars().all())

    part_stmt = select(Participant.room_id).where(
        Participant.user_id == user.id,
        Participant.is_deleted.is_(False),
    )
    participant_room_ids = set((await db.execute(part_stmt)).scalars().all())

    all_ids = owned_ids | participant_room_ids
    if not all_ids:
        return []

    stmt = (
        select(Room)
        .where(Room.id.in_(all_ids))
        .order_by(Room.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Инфо о комнате (участник)
# ---------------------------------------------------------------------------

@router.get("/{room_id}", response_model=RoomOut)

async def get_room(
    room: Room = Depends(get_current_organizer),
) -> Room:
    # get_current_organizer проверяет owner_id; для участника — отдельно
    return room


@router.get("/{room_id}/public", response_model=RoomOut)
async def get_room_for_participant(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    participant: Participant = Depends(get_current_participant),
) -> Room:
    return await get_room_or_404(db, room_id)


# ---------------------------------------------------------------------------
# Настройки комнаты (организатор, до draw)
# ---------------------------------------------------------------------------

@router.patch("/{room_id}", response_model=RoomOut)
async def update_room(
    payload: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    room: Room = Depends(get_current_organizer),
) -> Room:
    await ensure_room_editable(db, room)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if hasattr(value, "value"):  # Enum → str
            value = value.value
        setattr(room, key, value)

    await db.flush()
    await db.commit()
    await db.refresh(room)
    return room


# ---------------------------------------------------------------------------
# Приглашение
# ---------------------------------------------------------------------------

@router.post("/{room_id}/invite", response_model=InviteOut)
async def create_invite(
    payload: InviteCreate,
    db: AsyncSession = Depends(get_db),
    room: Room = Depends(get_current_organizer),
) -> dict:
    token = secrets.token_urlsafe(32)
    invite = Invite(
        room_id=room.id,
        token=token,
        telegram_id=payload.telegram_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days),
    )
    db.add(invite)
    await db.flush()
    await db.commit()
    await db.refresh(invite)

    deep_link = f"https://t.me/Coobee_Ai_bot?start=join_{token}"
    out = InviteOut.model_validate(invite, from_attributes=True)
    return {**out.model_dump(), "deep_link": deep_link}


# ---------------------------------------------------------------------------
# Вступление по токену
# ---------------------------------------------------------------------------

@router.post("/join/{token}", response_model=ParticipantOut)
async def join_by_token(
    token: str,
    payload: ParticipantCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Participant:
    stmt = select(Invite).where(Invite.token == token)
    invite = (await db.execute(stmt)).scalar_one_or_none()
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVITE_NOT_FOUND", "message": "Приглашение не найдено"},
        )
    if invite.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVITE_USED", "message": "Приглашение уже использовано"},
        )
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "INVITE_EXPIRED", "message": "Приглашение истекло"},
        )

    room = await get_room_or_404(db, invite.room_id)

    # Уже участник?
    existing = await db.execute(
        select(Participant).where(
            Participant.room_id == room.id,
            Participant.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_JOINED", "message": "Вы уже участник комнаты"},
        )

    # Prefill из профиля
    profile_stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    profile = (await db.execute(profile_stmt)).scalar_one_or_none()
    snapshot = build_prefill(profile, room.visibility_policy)["from_profile"]

    overrides = payload.model_dump(exclude_unset=True)
    # visibility — отдельно, после мержа
    visibility_override = overrides.pop("visibility", None)
    merged = merge_with_snapshot(snapshot, overrides)

    errors = validate_after_merge(merged)
    blocking = [e for e in errors if not e.startswith("interests_not_in_dict:")]
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PROFILE_INCOMPLETE",
                "message": "Заполните обязательные поля",
                "details": {"missing": blocking},
            },
        )

    visibility = validate_visibility(
        visibility_override or {},
        room.visibility_policy,
    )

    participant = Participant(
        room_id=room.id,
        user_id=user.id,
        display_name=merged.get("display_name") or user.username or "Участник",
        gender=merged["gender"],
        birth_date=merged.get("birth_date"),
        age=merged.get("age"),
        interests=merged.get("interests", []),
        hobbies=merged.get("hobbies"),
        antipathies=merged.get("antipathies"),
        allergies=merged.get("allergies"),
        constraints=merged.get("constraints"),
        brands=merged.get("brands"),
        sizes=merged.get("sizes"),
        budget_pref_min=merged.get("budget_pref_min"),
        budget_pref_max=merged.get("budget_pref_max"),
        pickup_point=merged.get("pickup_point"),
        visibility=visibility,
        source_profile_snapshot=snapshot,
        profile_completeness=compute_completeness(merged),
        status="profile_min" if len(merged.get("interests", [])) < 3 else "profile_full",
    )
    db.add(participant)

    invite.used_at = datetime.now(timezone.utc)

    await db.flush()
    await db.commit()
    await db.refresh(participant)

    # Уведомление организатору (best-effort, не блокирует)
    organizer = await db.get(User, room.owner_id)
    if organizer:
        await notif.notify_joined(
            db, organizer, participant.display_name, room.title
        )
        await db.commit()

    return participant


# ---------------------------------------------------------------------------
# Prefill (участник)
# ---------------------------------------------------------------------------

@router.get(
    "/{room_id}/participants/me/prefill",
    response_model=ParticipantPrefillOut,
)
async def get_prefill(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    room = await get_room_or_404(db, room_id)
    profile_stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    profile = (await db.execute(profile_stmt)).scalar_one_or_none()
    return build_prefill(profile, room.visibility_policy)


# ---------------------------------------------------------------------------
# Обновление анкеты (участник)
# ---------------------------------------------------------------------------

@router.patch("/{room_id}/participants/me", response_model=ParticipantOut)
async def update_my_profile(
    payload: ParticipantUpdate,
    db: AsyncSession = Depends(get_db),
    participant: Participant = Depends(get_current_participant),
) -> Participant:
    room = await db.get(Room, participant.room_id)
    if room is None:
        raise HTTPException(status_code=404, detail={"code": "ROOM_NOT_FOUND"})

    data = payload.model_dump(exclude_unset=True)
    visibility_override = data.pop("visibility", None)

    current = {
        "display_name": participant.display_name,
        "gender": participant.gender,
        "birth_date": participant.birth_date,
        "age": participant.age,
        "interests": participant.interests,
        "hobbies": participant.hobbies,
        "antipathies": participant.antipathies,
        "allergies": participant.allergies,
        "constraints": participant.constraints,
        "brands": participant.brands,
        "sizes": participant.sizes,
        "budget_pref_min": participant.budget_pref_min,
        "budget_pref_max": participant.budget_pref_max,
        "pickup_point": participant.pickup_point,
    }
    merged = merge_with_snapshot(current, data)

    errors = validate_after_merge(merged)
    blocking = [e for e in errors if not e.startswith("interests_not_in_dict:")]
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PROFILE_INCOMPLETE",
                "message": "Заполните обязательные поля",
                "details": {"missing": blocking},
            },
        )

    for key, value in merged.items():
        if hasattr(participant, key):
            setattr(participant, key, value)

    if visibility_override is not None:
        participant.visibility = validate_visibility(
            visibility_override, room.visibility_policy
        )

    participant.profile_completeness = compute_completeness(merged)
    if participant.profile_completeness >= 60:
        participant.status = "profile_full"
    elif participant.profile_completeness > 0:
        participant.status = "profile_min"

    await db.flush()
    await db.commit()
    await db.refresh(participant)
    return participant


# ---------------------------------------------------------------------------
# Превью «как меня видит Санта»
# ---------------------------------------------------------------------------

@router.get(
    "/{room_id}/participants/me/preview",
    response_model=ParticipantPreviewOut,
)
async def get_my_preview(
    participant: Participant = Depends(get_current_participant),
) -> dict:
    preview = build_preview(participant)
    return {
        "display_name": participant.display_name,
        "fields": preview["fields"],
        "warnings": preview["warnings"],
    }


# ---------------------------------------------------------------------------
# Список участников (имя + статус, без анкет и пар)
# ---------------------------------------------------------------------------

@router.get(
    "/{room_id}/participants",
    response_model=list[ParticipantPublicOut],
)
async def list_participants(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
) -> list[Participant]:
    stmt = select(Participant).where(
        Participant.room_id == participant.room_id,
    )
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Исключения (запрещённые пары) — только организатор, до draw
# ---------------------------------------------------------------------------

@router.get(
    "/{room_id}/exclusions",
    response_model=list[ExclusionOut],
)
async def list_exclusions(
    db: AsyncSession = Depends(get_db),
    room: Room = Depends(get_current_organizer),
) -> list[Exclusion]:
    stmt = select(Exclusion).where(Exclusion.room_id == room.id)
    return list((await db.execute(stmt)).scalars().all())


@router.post(
    "/{room_id}/exclusions",
    response_model=ExclusionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_exclusion(
    payload: ExclusionCreate,
    db: AsyncSession = Depends(get_db),
    room: Room = Depends(get_current_organizer),
) -> Exclusion:
    await ensure_room_editable(db, room)

    # Оба участника должны быть в этой комнате
    stmt = select(Participant).where(
        Participant.id.in_([payload.participant_a_id, payload.participant_b_id]),
        Participant.room_id == room.id,
        Participant.is_deleted.is_(False),
    )
    found = list((await db.execute(stmt)).scalars().all())
    if len(found) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "PARTICIPANT_NOT_IN_ROOM",
                "message": "Оба участника должны быть в комнате",
            },
        )

    # Не дублировать (симметрично)
    dup_stmt = select(Exclusion).where(
        Exclusion.room_id == room.id,
        Exclusion.participant_a_id.in_(
            [payload.participant_a_id, payload.participant_b_id]
        ),
        Exclusion.participant_b_id.in_(
            [payload.participant_a_id, payload.participant_b_id]
        ),
    )
    if (await db.execute(dup_stmt)).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXCLUSION_EXISTS",
                "message": "Такая пара уже запрещена",
            },
        )

    exclusion = Exclusion(
        room_id=room.id,
        participant_a_id=payload.participant_a_id,
        participant_b_id=payload.participant_b_id,
    )
    db.add(exclusion)
    await db.flush()
    await db.commit()
    await db.refresh(exclusion)
    return exclusion


@router.delete(
    "/{room_id}/exclusions/{exclusion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_exclusion(
    exclusion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    room: Room = Depends(get_current_organizer),
) -> Response:
    await ensure_room_editable(db, room)

    exclusion = await db.get(Exclusion, exclusion_id)
    if exclusion is None or exclusion.room_id != room.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXCLUSION_NOT_FOUND", "message": "Исключение не найдено"},
        )
    await db.delete(exclusion)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)