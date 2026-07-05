from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    module_id: Mapped[int | None] = mapped_column(
        ForeignKey("modules.id"), default=None
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    message_history: Mapped[list | None] = mapped_column(JSON, default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)

    student: Mapped["Student"] = relationship(back_populates="sessions")
    module: Mapped["Module | None"] = relationship(back_populates="sessions")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="session")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class MessageEntry(BaseModel):
    """One turn in a session's conversation history (stored in message_history
    JSON). `prompt_key` records which pedagogical strategy was active when the
    assistant produced this message, enabling per-turn traceability (RF-18)."""

    role: str
    content: str
    timestamp: str
    prompt_key: str | None = None


class SessionCreate(BaseModel):
    student_id: int
    module_id: int | None = None


class SessionRead(BaseModel):
    id: int
    student_id: int
    module_id: int | None
    started_at: datetime
    ended_at: datetime | None
    status: str
    message_history: list[MessageEntry] | None
    summary: str | None

    model_config = {"from_attributes": True}


class SessionUpdate(BaseModel):
    status: str | None = None
    summary: str | None = None
