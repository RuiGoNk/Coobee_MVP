import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CatalogItem(Base):
    __tablename__ = "catalog"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    price_min: Mapped[int | None]
    price_max: Mapped[int | None]
    tags: Mapped[list | None] = mapped_column(JSONB)              # значения из HOBBY/STYLE
    image_url: Mapped[str | None] = mapped_column(String(512))
    marketplace_url: Mapped[str | None] = mapped_column(String(512))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_paired: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_type: Mapped[str] = mapped_column(String(16), default="physical")  # physical|digital|certificate
    delivery_regions: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)