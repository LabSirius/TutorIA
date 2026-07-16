from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AnalyticsEventCreate(BaseModel):
    student_id: int
    event_type: str
    data: dict | None = None


class AnalyticsEventRead(BaseModel):
    id: int
    student_id: int
    event_type: str
    data: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseSummary(BaseModel):
    active_students: int
    average_progress: float
    approval_rate: float


class StudentDetail(BaseModel):
    student_id: int
    name: str
    modules_completed: int
    total_sessions: int
    total_time_minutes: float
    average_score: float | None


class RiskAlert(BaseModel):
    student_id: int
    name: str
    alert_type: str
    detail: str


# ---------------------------------------------------------------------------
# Conversation traceability for teachers (RF-18)
# ---------------------------------------------------------------------------

class ConversationSummary(BaseModel):
    session_id: int
    module_id: int | None
    subject_id: int | None
    module_name: str | None
    subject_name: str | None
    started_at: datetime
    ended_at: datetime | None
    message_count: int
    # None while the session is still open (no ended_at to measure against).
    duration_minutes: float | None


class ConversationsPage(BaseModel):
    items: list[ConversationSummary]
    total: int
    page: int
    page_size: int
    has_more: bool


class TranscriptMessage(BaseModel):
    role: str
    content: str
    timestamp: str | None = None
    # Which pedagogical strategy produced this turn; null on student turns and
    # on messages recorded before prompt_key existed.
    prompt_key: str | None = None


class SessionMetadata(BaseModel):
    session_id: int
    student_id: int
    module_id: int | None
    subject_id: int | None
    started_at: datetime
    ended_at: datetime | None


class TranscriptResponse(BaseModel):
    session_metadata: SessionMetadata
    messages: list[TranscriptMessage]
