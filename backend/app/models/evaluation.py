from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class Evaluation(Base):
    """This model is named `evaluations` for historical reasons. Semantically it
    represents feedback events in TutorIA's continuous formative feedback system,
    not summative assessments. See RF-15 in the requirements document. The table
    name is intentionally kept to avoid a destructive migration; the HTTP surface
    is exposed under /api/feedback (see routers/feedback.py)."""

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("sessions.id"), default=None
    )
    eval_type: Mapped[str] = mapped_column(String(50), nullable=False)
    questions: Mapped[dict | None] = mapped_column(JSON, default=None)
    answers: Mapped[dict | None] = mapped_column(JSON, default=None)
    score: Mapped[float | None] = mapped_column(Float, default=None)
    feedback: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    student: Mapped["Student"] = relationship(back_populates="evaluations")
    module: Mapped["Module"] = relationship(back_populates="evaluations")
    session: Mapped["Session | None"] = relationship(back_populates="evaluations")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class EvaluationCreate(BaseModel):
    student_id: int
    module_id: int
    session_id: int | None = None
    eval_type: str
    questions: dict | None = None


class EvaluationRead(BaseModel):
    id: int
    student_id: int
    module_id: int
    session_id: int | None
    eval_type: str
    questions: dict | None
    answers: dict | None
    score: float | None
    feedback: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationSubmit(BaseModel):
    answers: dict
