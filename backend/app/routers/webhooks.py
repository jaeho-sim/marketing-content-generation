"""
GCS → Pub/Sub push webhook  +  local-dev simulate endpoint.

Pub/Sub push message shape:
{
  "message": {
    "data": "<base64-encoded GCS Object Notification JSON>",
    "messageId": "...",
    "publishTime": "..."
  },
  "subscription": "projects/.../subscriptions/..."
}

GCS Object Notification fields used:
  eventType   – "OBJECT_FINALIZE" on successful upload
  name        – GCS object key
  contentType – MIME type
  size        – object size in bytes (string)

We ack immediately (200) and hand the heavy work to a background task so
Whisper + Claude don't consume the Pub/Sub ack deadline.
"""
import asyncio
import base64
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal, get_db
from app.models.draft import Draft
from app.models.event import Event
from app.models.media import Media
from app.services.draft_generation import generate_draft
from app.services.transcription import transcribe_gcs_object

log = structlog.get_logger()
settings = get_settings()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Dedicated thread pool — keeps the event loop free during CPU/IO-bound work.
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pipeline")


# ---------------------------------------------------------------------------
# Pub/Sub push endpoint
# ---------------------------------------------------------------------------

@router.post("/gcs")
async def gcs_pubsub_push(
    request: Request,
    background_tasks: BackgroundTasks,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if token != settings.pubsub_webhook_token:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    body = await request.json()
    try:
        notification = json.loads(
            base64.b64decode(body["message"]["data"]).decode()
        )
    except Exception:
        log.warning("webhook_invalid_payload")
        return {"status": "ignored"}

    if notification.get("eventType") != "OBJECT_FINALIZE":
        return {"status": "ignored"}

    gcs_key: str = notification.get("name", "")
    if not gcs_key.startswith("media/"):
        return {"status": "ignored"}

    content_type: str | None = notification.get("contentType")
    size_bytes = int(notification.get("size", 0)) or None

    log.info("gcs_upload_finalized", gcs_key=gcs_key, content_type=content_type)

    result = await db.execute(select(Media).where(Media.gcs_key == gcs_key))
    media = result.scalar_one_or_none()
    if media is None:
        log.warning("no_media_row_for_key", gcs_key=gcs_key)
        return {"status": "ignored"}

    await _mark_uploaded(media, size_bytes, content_type, db)
    background_tasks.add_task(
        _run_pipeline, str(media.id), str(media.event_id), gcs_key, content_type
    )
    return {"status": "accepted"}


# ---------------------------------------------------------------------------
# Dev-only simulate endpoint
# ---------------------------------------------------------------------------

class SimulateRequest(BaseModel):
    event_id: uuid.UUID


@router.post(
    "/gcs/simulate",
    summary="[DEV] Trigger the pipeline for an event without a real GCS upload",
    include_in_schema=settings.app_env != "production",
)
async def simulate_gcs_upload(
    payload: SimulateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if settings.app_env == "production":
        raise HTTPException(status_code=404)

    result = await db.execute(select(Media).where(Media.event_id == payload.event_id))
    media = result.scalar_one_or_none()
    if media is None:
        raise HTTPException(status_code=404, detail="No media row for this event")

    await _mark_uploaded(media, size_bytes=None, content_type="audio/mpeg", db=db)
    background_tasks.add_task(
        _run_pipeline, str(media.id), str(media.event_id), media.gcs_key, "audio/mpeg"
    )
    return {"status": "pipeline_started", "event_id": str(payload.event_id)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _mark_uploaded(
    media: Media, size_bytes: int | None, content_type: str | None, db: AsyncSession
) -> None:
    media.content_type = content_type
    media.size_bytes = size_bytes
    media.uploaded_at = datetime.now(timezone.utc)
    media.transcription_status = "processing"

    event_result = await db.execute(select(Event).where(Event.id == media.event_id))
    event = event_result.scalar_one_or_none()
    if event:
        event.status = "transcribing"

    await db.commit()


async def _run_pipeline(
    media_id: str, event_id: str, gcs_key: str, content_type: str | None
) -> None:
    loop = asyncio.get_running_loop()

    async with AsyncSessionLocal() as db:
        try:
            # ── Transcription ──────────────────────────────────────────────
            transcript: str = await loop.run_in_executor(
                _executor, partial(transcribe_gcs_object, gcs_key, content_type)
            )

            media_result = await db.execute(select(Media).where(Media.id == uuid.UUID(media_id)))
            media = media_result.scalar_one()
            media.transcript = transcript
            media.transcription_status = "completed"
            media.transcribed_at = datetime.now(timezone.utc)

            event_result = await db.execute(select(Event).where(Event.id == uuid.UUID(event_id)))
            event = event_result.scalar_one()
            event.status = "drafting"
            await db.commit()

            # ── Draft generation ───────────────────────────────────────────
            draft_data: dict = await loop.run_in_executor(
                _executor, partial(generate_draft, transcript, event.title)
            )

            draft = Draft(
                event_id=uuid.UUID(event_id),
                content=draft_data["content"],
                llm_provider="claude",
                llm_model=draft_data["model"],
                prompt_tokens=draft_data["prompt_tokens"],
                completion_tokens=draft_data["completion_tokens"],
                status="completed",
                generated_at=datetime.now(timezone.utc),
            )
            db.add(draft)
            event.status = "draft_ready"
            await db.commit()
            log.info("pipeline_complete", event_id=event_id)

        except Exception as exc:
            log.error("pipeline_error", event_id=event_id, error=str(exc), exc_info=True)
            await _mark_failed(media_id, event_id, str(exc))


async def _mark_failed(media_id: str, event_id: str, error: str) -> None:
    try:
        async with AsyncSessionLocal() as db:
            media_result = await db.execute(select(Media).where(Media.id == uuid.UUID(media_id)))
            media = media_result.scalar_one()
            media.transcription_status = "failed"
            media.transcription_error = error

            event_result = await db.execute(select(Event).where(Event.id == uuid.UUID(event_id)))
            event = event_result.scalar_one()
            event.status = "failed"
            await db.commit()
    except Exception:
        log.exception("failed_to_mark_failure", event_id=event_id)
