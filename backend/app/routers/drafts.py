import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.draft import Draft
from app.schemas.draft import DraftResponse

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.get("/by-event/{event_id}", response_model=DraftResponse)
async def get_draft_by_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Draft).where(Draft.event_id == event_id))
    draft = result.scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found for this event")
    return DraftResponse.model_validate(draft)


@router.get("/{draft_id}", response_model=DraftResponse)
async def get_draft(draft_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Draft).where(Draft.id == draft_id))
    draft = result.scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return DraftResponse.model_validate(draft)
