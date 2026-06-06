from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import SyncBlob, User

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncBlobRequest(BaseModel):
    record_id: UUID
    encrypted_blob: str = Field(min_length=1)
    version: int = Field(ge=1, default=1)


class SyncBlobResponse(BaseModel):
    record_id: UUID
    encrypted_blob: str
    version: int
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/blobs", response_model=list[SyncBlobResponse])
async def list_blobs(
    since: str | None = Query(None, description="ISO 8601 timestamp"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SyncBlob]:
    stmt = select(SyncBlob).where(SyncBlob.user_id == user.id)

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            stmt = stmt.where(SyncBlob.updated_at > since_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Geçersiz since formatı. ISO 8601 bekleniyor.")

    stmt = stmt.order_by(SyncBlob.updated_at.asc())
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return rows


@router.post("/blobs", response_model=SyncBlobResponse, status_code=status.HTTP_201_CREATED)
async def upsert_blob(
    body: SyncBlobRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncBlob:
    result = await db.execute(
        select(SyncBlob).where(
            SyncBlob.user_id == user.id,
            SyncBlob.record_id == body.record_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if body.version < existing.version:
            raise HTTPException(
                status_code=409,
                detail=f"Version conflict: server has {existing.version}, client sent {body.version}",
            )
        existing.encrypted_blob = body.encrypted_blob
        existing.version = body.version
        existing.updated_at = datetime.now(existing.updated_at.tzinfo)
        await db.commit()
        await db.refresh(existing)
        return existing

    item = SyncBlob(
        user_id=user.id,
        record_id=body.record_id,
        encrypted_blob=body.encrypted_blob,
        version=body.version,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/blobs/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blob(
    record_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(SyncBlob).where(
            SyncBlob.user_id == user.id,
            SyncBlob.record_id == record_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Sync blob bulunamadı")
    await db.delete(item)
    await db.commit()


# Legacy routes — redirect clients to opaque blob API
@router.get("/items", deprecated=True)
async def list_items_legacy(
    user: User = Depends(get_current_user),
) -> list:
    return []


@router.post("/items", deprecated=True, status_code=status.HTTP_410_GONE)
async def upsert_item_legacy() -> None:
    raise HTTPException(
        status_code=410,
        detail="Legacy sync API removed. Use POST /sync/blobs with opaque encrypted_blob.",
    )
