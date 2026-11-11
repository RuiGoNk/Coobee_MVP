import uuid
from pydantic import BaseModel


class CatalogItemIn(BaseModel):
    external_id: str | None = None
    title: str
    description: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    tags: list[str] | None = None
    image_url: str | None = None
    marketplace_url: str | None = None
    is_available: bool = True
    is_paired: bool = False
    delivery_type: str = "physical"
    delivery_regions: list[str] | None = None
    details: dict | None = None


class CatalogItemOut(CatalogItemIn):
    id: uuid.UUID
    model_config = {"from_attributes": True}