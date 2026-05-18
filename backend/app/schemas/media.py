import uuid
from datetime import datetime
from pydantic import BaseModel


class MediaResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    gcs_key: str
    content_type: str | None
    size_bytes: int | None
    transcript: str | None
    transcription_status: str
    uploaded_at: datetime | None
    transcribed_at: datetime | None

    model_config = {"from_attributes": True}
