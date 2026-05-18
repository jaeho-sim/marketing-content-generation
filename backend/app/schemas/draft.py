import uuid
from datetime import datetime
from pydantic import BaseModel


class DraftResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    content: str
    llm_provider: str
    llm_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    status: str
    generated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
