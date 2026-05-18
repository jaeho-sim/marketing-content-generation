import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    author_id: str = Field(..., min_length=1, max_length=255)
    author_role: Literal["reviewer", "producer"]
    body: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    author_id: str
    author_role: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionCreate(BaseModel):
    reviewer_id: str = Field(..., min_length=1, max_length=255)
    decision: Literal["approved", "rejected"]


class ReviewResponse(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    reviewer_id: str | None
    decision: str | None
    decided_at: datetime | None
    comments: list[CommentResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
