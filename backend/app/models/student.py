from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------

class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    global_level: Mapped[str] = mapped_column(
        String(20), default="beginner"
    )
    interests: Mapped[dict | None] = mapped_column(JSON, default=None)
    preferences: Mapped[dict | None] = mapped_column(JSON, default=None)

    # Gamification (RF-16, RF-24). student_badges is the source of truth for
    # earned badges; badges_earned is a denormalized cache for fast reads.
    xp_points: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    current_streak_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    badges_earned: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="student")
    progress: Mapped[list["StudentProgress"]] = relationship(back_populates="student")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="student")
    student_badges: Mapped[list["StudentBadge"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class StudentProgress(Base):
    __tablename__ = "student_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    module_level: Mapped[str] = mapped_column(String(20), default="not_started")
    mastered_concepts: Mapped[dict | None] = mapped_column(JSON, default=None)
    pending_concepts: Mapped[dict | None] = mapped_column(JSON, default=None)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_session_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    student: Mapped["Student"] = relationship(back_populates="progress")
    module: Mapped["Module"] = relationship(back_populates="student_progress")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class StudentCreate(BaseModel):
    name: str
    email: str
    interests: dict | None = None
    preferences: dict | None = None


class StudentRead(BaseModel):
    id: int
    name: str
    email: str
    registered_at: datetime
    global_level: str
    interests: dict | None
    preferences: dict | None
    xp_points: int
    current_streak_days: int
    badges_earned: list

    model_config = {"from_attributes": True}


class StudentUpdate(BaseModel):
    name: str | None = None
    global_level: str | None = None
    interests: dict | None = None
    preferences: dict | None = None


class StudentProgressRead(BaseModel):
    id: int
    student_id: int
    module_id: int
    module_level: str
    mastered_concepts: dict | None
    pending_concepts: dict | None
    attempts: int
    last_session_at: datetime | None

    model_config = {"from_attributes": True}
