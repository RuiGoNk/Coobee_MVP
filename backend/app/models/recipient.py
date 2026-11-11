import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, SmallInteger, DateTime, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Recipient(Base):
    __tablename__ = "recipients"
    __table_args__ = (
        CheckConstraint("birth_date IS NOT NULL OR age IS NOT NULL", name="ck_recipient_age_present"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    relationship: Mapped[str] = mapped_column(String(32))
    gender: Mapped[str] = mapped_column(String(16), default="unisex")
    birth_date: Mapped[date | None] = mapped_column(Date)
    age: Mapped[int | None] = mapped_column(SmallInteger)          # если дата неизвестна
    age_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    occasion: Mapped[str | None] = mapped_column(String(32))
    relationship_level: Mapped[str | None] = mapped_column(String(16))
    budget_range: Mapped[str | None] = mapped_column(String(16))
    details: Mapped[dict | None] = mapped_column(JSONB)            # interests, style, family, pets, delivery...
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)