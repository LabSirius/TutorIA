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
