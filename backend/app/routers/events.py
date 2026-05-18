import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.event import Event
from app.models.media import Media
from app.schemas.event import EventCreate, EventResponse, EventStatusResponse
from app.services import gcs

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventCreate, db: AsyncSession = Depends(get_db)):
    event = Event(
        title=payload.title,
        description=payload.description,
        producer_id=payload.producer_id,
        status="pending_upload",
    )
    db.add(event)
    await db.flush()  # assign UUID before generating GCS key

    gcs_key = gcs.generate_media_gcs_key(event.id)
    event.media_gcs_key = gcs_key

    media = Media(event_id=event.id, gcs_key=gcs_key, transcription_status="pending")
    db.add(media)
    await db.flush()

    presigned_url = gcs.generate_presigned_upload_url(gcs_key)
    await db.commit()
    await db.refresh(event)

    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        producer_id=event.producer_id,
        status=event.status,
        media_gcs_key=event.media_gcs_key,
        presigned_upload_url=presigned_url,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("", response_model=list[EventResponse])
async def list_events(producer_id: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Event).order_by(Event.created_at.desc())
    if producer_id:
        query = query.where(Event.producer_id == producer_id)
    result = await db.execute(query)
    return [_to_response(e) for e in result.scalars().all()]


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return _to_response(await _get_or_404(event_id, db))


@router.get("/{event_id}/status", response_model=EventStatusResponse)
async def get_event_status(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.media),
            selectinload(Event.draft).selectinload("review"),
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventStatusResponse(
        id=event.id,
        title=event.title,
        status=event.status,
        transcript_status=event.media.transcription_status if event.media else None,
        draft_status=event.draft.status if event.draft else None,
        review_decision=(
            event.draft.review.decision
            if event.draft and event.draft.review
            else None
        ),
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


async def _get_or_404(event_id: uuid.UUID, db: AsyncSession) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _to_response(e: Event) -> EventResponse:
    return EventResponse(
        id=e.id,
        title=e.title,
        description=e.description,
        producer_id=e.producer_id,
        status=e.status,
        media_gcs_key=e.media_gcs_key,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )
