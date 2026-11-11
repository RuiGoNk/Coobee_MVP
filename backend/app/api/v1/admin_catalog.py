import uuid
import pathlib
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import require_admin
from app.db.session import SessionLocal
from app.models.catalog import CatalogItem
from app.schemas.catalog import CatalogItemIn, CatalogItemOut

router = APIRouter(prefix="/admin/catalog", tags=["admin"], dependencies=[Depends(require_admin)])

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


async def get_db():
    async with SessionLocal() as s:
        yield s


@router.post("", response_model=CatalogItemOut, status_code=201)
async def create_item(payload: CatalogItemIn, db: AsyncSession = Depends(get_db)):
    item = CatalogItem(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("", response_model=list[CatalogItemOut])
async def list_items(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    stmt = select(CatalogItem).order_by(CatalogItem.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.post("/batch")
async def create_batch(payload: list[CatalogItemIn], db: AsyncSession = Depends(get_db)):
    created, errors = [], []
    for i, p in enumerate(payload):
        try:
            item = CatalogItem(**p.model_dump())
            db.add(item)
            await db.flush()
            created.append(str(item.id))
        except Exception as e:  # noqa: BLE001
            errors.append({"row": i, "error": str(e)})
            await db.rollback()
    await db.commit()
    return {"created": len(created), "errors": errors}


@router.post("/{item_id}/image")
async def upload_image(item_id: uuid.UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    item = await db.get(CatalogItem, item_id)
    if not item:
        raise HTTPException(404, "item not found")

    ext = pathlib.Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "unsupported image extension")

    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > settings.MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(400, "image too large")

    sig = data[:12]
    is_jpeg = sig[:3] == b"\xff\xd8\xff"
    is_png = sig[:8] == b"\x89PNG\r\n\x1a\n"
    is_webp = sig[:4] == b"RIFF" and sig[8:12] == b"WEBP"
    if not (is_jpeg or is_png or is_webp):
        raise HTTPException(400, "not a valid image")

    dest_dir = pathlib.Path(settings.STATIC_DIR) / "uploads" / "catalog"
    dest_dir.mkdir(parents=True, exist_ok=True)
    save_ext = ".jpg" if ext == ".jpeg" else ext
    dest = dest_dir / f"{item_id}{save_ext}"
    dest.write_bytes(data)
    item.image_url = f"/static/uploads/catalog/{item_id}{save_ext}"
    await db.commit()
    return {"image_url": item.image_url}