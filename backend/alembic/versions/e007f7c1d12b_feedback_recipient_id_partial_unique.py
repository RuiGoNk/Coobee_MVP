"""feedback recipient_id partial unique

Revision ID: e007f7c1d12b
Revises: 66ecb46e016e
Create Date: 2026-11-11 19:33:04.217312
"""
from alembic import op
import sqlalchemy as sa


revision = 'e007f7c1d12b'
down_revision = '66ecb46e016e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('feedback', sa.Column('recipient_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_feedback_recipient', 'feedback', 'recipients',
        ['recipient_id'], ['id'], ondelete='CASCADE',
    )
    # старый неуникальный индекс больше не нужен
    op.drop_index('ix_feedback_user_item', table_name='feedback')
    # частичные unique-индексы
    op.create_index(
        'uq_feedback_recipient',
        'feedback',
        ['user_id', 'item_id', 'recipient_id'],
        unique=True,
        postgresql_where=sa.text("context = 'recipient'"),
    )
    op.create_index(
        'uq_feedback_self',
        'feedback',
        ['user_id', 'item_id'],
        unique=True,
        postgresql_where=sa.text("context = 'self_wishlist'"),
    )


def downgrade() -> None:
    op.drop_index('uq_feedback_self', table_name='feedback')
    op.drop_index('uq_feedback_recipient', table_name='feedback')
    op.create_index('ix_feedback_user_item', 'feedback', ['user_id', 'item_id'], unique=False)
    op.drop_constraint('fk_feedback_recipient', 'feedback', type_='foreignkey')
    op.drop_column('feedback', 'recipient_id')
