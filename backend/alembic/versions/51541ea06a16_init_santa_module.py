"""init santa module

Revision ID: 51541ea06a16
Revises: 1039b406c91c
Create Date: 2026-11-12 13:12:26.402008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '51541ea06a16'
down_revision = '1039b406c91c'
branch_labels = None
depends_on = None


# ENUM-типы модуля santa. Создаём явно, чтобы:
# 1) не падать на повторном upgrade;
# 2) удалять в downgrade;
# 3) в create_table использовать create_type=False.
SANTA_ENUMS = (
    "santa_room_status",
    "santa_visibility_policy",
    "santa_anonymity_mode",
    "santa_join_policy",
    "santa_gender",
    "santa_participant_status",
    "santa_draw_status",
    "santa_gift_status",
    "santa_suggestion_source",
)


def upgrade() -> None:
    bind = op.get_bind()

    # --- Явное создание ENUM-типов ---
    sa.Enum(
        "draft", "collecting", "drawn", "in_progress", "completed", "archived",
        name="santa_room_status",
    ).create(bind, checkfirst=True)
    sa.Enum("open", "balanced", "minimal", name="santa_visibility_policy").create(
        bind, checkfirst=True
    )
    sa.Enum("full", "reveal_after", "signed", name="santa_anonymity_mode").create(
        bind, checkfirst=True
    )
    sa.Enum("link", "code", "invite", name="santa_join_policy").create(
        bind, checkfirst=True
    )
    sa.Enum(
        "male", "female", "other", "prefer_not_to_say", name="santa_gender"
    ).create(bind, checkfirst=True)
    sa.Enum(
        "invited", "joined", "profile_min", "profile_full",
        name="santa_participant_status",
    ).create(bind, checkfirst=True)
    sa.Enum("generating", "ready", name="santa_draw_status").create(
        bind, checkfirst=True
    )
    sa.Enum(
        "pending", "chosen", "shipped", "delivered", name="santa_gift_status"
    ).create(bind, checkfirst=True)
    sa.Enum(
        "curated", "llm", "marketplace", name="santa_suggestion_source"
    ).create(bind, checkfirst=True)

    # --- Таблицы ---

    op.create_table(
        'santa_notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_santa_notifications_user', 'santa_notifications', ['user_id'], unique=False)

    op.create_table(
        'santa_rooms',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_date', sa.Date(), nullable=True),
        sa.Column('budget_min', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('budget_max', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('tz', sa.String(length=64), nullable=False),
        sa.Column('status', postgresql.ENUM(name='santa_room_status', create_type=False), nullable=False),
        sa.Column('anonymity_mode', postgresql.ENUM(name='santa_anonymity_mode', create_type=False), nullable=False),
        sa.Column('join_policy', postgresql.ENUM(name='santa_join_policy', create_type=False), nullable=False),
        sa.Column('visibility_policy', postgresql.ENUM(name='santa_visibility_policy', create_type=False), nullable=False),
        sa.Column('max_participants', sa.SmallInteger(), nullable=False),
        sa.Column('require_min_profile', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('budget_max >= budget_min', name='ck_santa_room_budget_range'),
        sa.CheckConstraint('budget_min >= 0', name='ck_santa_room_budget_min'),
        sa.CheckConstraint('max_participants BETWEEN 3 AND 30', name='ck_santa_room_max_participants'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_santa_rooms_owner', 'santa_rooms', ['owner_id'], unique=False)
    op.create_index('ix_santa_rooms_status', 'santa_rooms', ['status'], unique=False)

    op.create_table(
        'santa_draws',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('room_id', sa.UUID(), nullable=False),
        sa.Column('drawn_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('drawn_by', sa.UUID(), nullable=True),
        sa.Column('algorithm_version', sa.String(length=32), nullable=False),
        sa.Column('status', postgresql.ENUM(name='santa_draw_status', create_type=False), nullable=False),
        sa.ForeignKeyConstraint(['drawn_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['room_id'], ['santa_rooms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_santa_draws_room', 'santa_draws', ['room_id'], unique=False)

    op.create_table(
        'santa_invites',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('room_id', sa.UUID(), nullable=False),
        sa.Column('token', sa.String(length=128), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['room_id'], ['santa_rooms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token', name='uq_santa_invite_token'),
    )
    op.create_index('ix_santa_invites_room', 'santa_invites', ['room_id'], unique=False)

    op.create_table(
        'santa_participants',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('room_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('gender', postgresql.ENUM(name='santa_gender', create_type=False), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('age', sa.SmallInteger(), nullable=True),
        sa.Column('age_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('interests', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('hobbies', sa.Text(), nullable=True),
        sa.Column('antipathies', sa.Text(), nullable=True),
        sa.Column('allergies', sa.Text(), nullable=True),
        sa.Column('constraints', sa.Text(), nullable=True),
        sa.Column('brands', sa.Text(), nullable=True),
        sa.Column('sizes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('budget_pref_min', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('budget_pref_max', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('pickup_point', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('visibility', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('source_profile_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('profile_completeness', sa.SmallInteger(), nullable=False),
        sa.Column('status', postgresql.ENUM(name='santa_participant_status', create_type=False), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('age IS NULL OR (age BETWEEN 14 AND 120)', name='ck_santa_participant_age_range'),
        sa.CheckConstraint('array_length(interests, 1) >= 1', name='ck_santa_participant_interests_min'),
        sa.CheckConstraint('birth_date IS NOT NULL OR age IS NOT NULL', name='ck_santa_participant_age_present'),
        sa.ForeignKeyConstraint(['room_id'], ['santa_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('room_id', 'user_id', name='uq_santa_participant_room_user'),
    )
    op.create_index('ix_santa_participants_interests_gin', 'santa_participants', ['interests'], unique=False, postgresql_using='gin')
    op.create_index('ix_santa_participants_room', 'santa_participants', ['room_id'], unique=False)

    op.create_table(
        'santa_assignments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('draw_id', sa.UUID(), nullable=False),
        sa.Column('santa_participant_id', sa.UUID(), nullable=True),
        sa.Column('santee_participant_id', sa.UUID(), nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gift_status', postgresql.ENUM(name='santa_gift_status', create_type=False), nullable=False),
        sa.CheckConstraint('santa_participant_id IS NULL OR santee_participant_id IS NULL OR santa_participant_id <> santee_participant_id', name='ck_santa_assignment_no_self'),
        sa.ForeignKeyConstraint(['draw_id'], ['santa_draws.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['santa_participant_id'], ['santa_participants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['santee_participant_id'], ['santa_participants.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_santa_assignments_santa', 'santa_assignments', ['santa_participant_id'], unique=False)
    op.create_index('ix_santa_assignments_draw', 'santa_assignments', ['draw_id'], unique=False)

    op.create_table(
        'santa_exclusions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('room_id', sa.UUID(), nullable=False),
        sa.Column('participant_a_id', sa.UUID(), nullable=False),
        sa.Column('participant_b_id', sa.UUID(), nullable=False),
        sa.CheckConstraint('participant_a_id <> participant_b_id', name='ck_santa_exclusion_distinct'),
        sa.ForeignKeyConstraint(['participant_a_id'], ['santa_participants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_b_id'], ['santa_participants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_id'], ['santa_rooms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('room_id', 'participant_a_id', 'participant_b_id', name='uq_santa_exclusion_pair'),
    )

    op.create_table(
        'santa_gift_suggestions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('assignment_id', sa.UUID(), nullable=False),
        sa.Column('generation', sa.SmallInteger(), nullable=False),
        sa.Column('external_id', sa.String(length=64), nullable=True),
        sa.Column('idea_title', sa.String(length=300), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('price_min', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('price_max', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('score', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('source', postgresql.ENUM(name='santa_suggestion_source', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assignment_id'], ['santa_assignments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_santa_suggestions_assignment_gen', 'santa_gift_suggestions', ['assignment_id', 'generation'], unique=False)

    op.create_table(
        'santa_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('room_id', sa.UUID(), nullable=False),
        sa.Column('assignment_id', sa.UUID(), nullable=False),
        sa.Column('from_participant_id', sa.UUID(), nullable=True),
        sa.Column('to_participant_id', sa.UUID(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_revealed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assignment_id'], ['santa_assignments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_participant_id'], ['santa_participants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['room_id'], ['santa_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_participant_id'], ['santa_participants.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_santa_messages_assignment', 'santa_messages', ['assignment_id'], unique=False)
    op.create_index('ix_santa_messages_room', 'santa_messages', ['room_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_santa_messages_room', table_name='santa_messages')
    op.drop_index('ix_santa_messages_assignment', table_name='santa_messages')
    op.drop_table('santa_messages')

    op.drop_index('ix_santa_suggestions_assignment_gen', table_name='santa_gift_suggestions')
    op.drop_table('santa_gift_suggestions')

    op.drop_table('santa_exclusions')

    op.drop_index('ix_santa_assignments_draw', table_name='santa_assignments')
    op.drop_index('ix_santa_assignments_santa', table_name='santa_assignments')
    op.drop_table('santa_assignments')

    op.drop_index('ix_santa_participants_interests_gin', table_name='santa_participants', postgresql_using='gin')
    op.drop_index('ix_santa_participants_room', table_name='santa_participants')
    op.drop_table('santa_participants')

    op.drop_index('ix_santa_invites_room', table_name='santa_invites')
    op.drop_table('santa_invites')

    op.drop_index('ix_santa_draws_room', table_name='santa_draws')
    op.drop_table('santa_draws')

    op.drop_index('ix_santa_rooms_status', table_name='santa_rooms')
    op.drop_index('ix_santa_rooms_owner', table_name='santa_rooms')
    op.drop_table('santa_rooms')

    op.drop_index('ix_santa_notifications_user', table_name='santa_notifications')
    op.drop_table('santa_notifications')

    # Удаление ENUM-типов (после всех таблиц)
    bind = op.get_bind()
    for enum_name in (
        "santa_suggestion_source",
        "santa_gift_status",
        "santa_draw_status",
        "santa_participant_status",
        "santa_gender",
        "santa_join_policy",
        "santa_anonymity_mode",
        "santa_visibility_policy",
        "santa_room_status",
    ):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)