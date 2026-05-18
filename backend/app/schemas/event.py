import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    producer_id: str = Field(..., min_length=1, max_length=255)


class EventResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    producer_id: str
    status: str
    media_gcs_key: str | None
    presigned_upload_url: str | None = None  # only populated on create
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventStatusResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    transcript_status: str | None = None
    draft_status: str | None = None
    review_decision: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
