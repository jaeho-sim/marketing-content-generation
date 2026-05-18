import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    producer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    media_gcs_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Pipeline status — see STATUS_TRANSITIONS in routers/events.py for valid values
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending_upload")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    media: Mapped["Media"] = relationship("Media", back_populates="event", uselist=False)
    draft: Mapped["Draft"] = relationship("Draft", back_populates="event", uselist=False)
