import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.draft import Draft
from app.models.event import Event
from app.models.review import Review, Comment
from app.schemas.review import ReviewResponse, CommentCreate, CommentResponse, DecisionCreate

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/by-draft/{draft_id}", response_model=ReviewResponse)
async def get_review(draft_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return ReviewResponse.model_validate(await _get_or_create_review(draft_id, db))


@router.post(
    "/by-draft/{draft_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    draft_id: uuid.UUID, payload: CommentCreate, db: AsyncSession = Depends(get_db)
):
    review = await _get_or_create_review(draft_id, db)
    comment = Comment(
        review_id=review.id,
        author_id=payload.author_id,
        author_role=payload.author_role,
        body=payload.body,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentResponse.model_validate(comment)


@router.post("/by-draft/{draft_id}/decision", response_model=ReviewResponse)
async def submit_decision(
    draft_id: uuid.UUID, payload: DecisionCreate, db: AsyncSession = Depends(get_db)
):
    review = await _get_or_create_review(draft_id, db)
    if review.decision is not None:
        raise HTTPException(status_code=409, detail="Decision already submitted")

    review.reviewer_id = payload.reviewer_id
    review.decision = payload.decision
    review.decided_at = datetime.now(timezone.utc)

    # Mirror decision onto the parent event
    draft_result = await db.execute(select(Draft).where(Draft.id == draft_id))
    draft = draft_result.scalar_one_or_none()
    if draft:
        event_result = await db.execute(select(Event).where(Event.id == draft.event_id))
        event = event_result.scalar_one_or_none()
        if event:
            event.status = payload.decision  # "approved" | "rejected"

    await db.commit()

    result = await db.execute(
        select(Review).where(Review.id == review.id).options(selectinload(Review.comments))
    )
    return ReviewResponse.model_validate(result.scalar_one())


async def _get_or_create_review(draft_id: uuid.UUID, db: AsyncSession) -> Review:
    draft_result = await db.execute(select(Draft).where(Draft.id == draft_id))
    if draft_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Draft not found")

    result = await db.execute(
        select(Review)
        .where(Review.draft_id == draft_id)
        .options(selectinload(Review.comments))
    )
    review = result.scalar_one_or_none()
    if review is None:
        review = Review(draft_id=draft_id)
        db.add(review)
        await db.commit()
        await db.refresh(review)
        review.comments = []
    return review
