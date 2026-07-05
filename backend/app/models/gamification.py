from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------

class Badge(Base):
    """A gamification reward the student can earn (RF-16, RF-24).

    `criteria_json` holds a structured rule that gamification_service interprets
    at award time (implemented in a later step). The mechanics are a proposal to
    be refined with the pedagogical team, so the rules are kept intentionally
    simple and data-driven rather than hard-coded.
    """

    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    icon_url: Mapped[str | None] = mapped_column(String(500), default=None)
    criteria_json: Mapped[dict | None] = mapped_column(JSONB, default=None)

    student_badges: Mapped[list["StudentBadge"]] = relationship(
        back_populates="badge", cascade="all, delete-orphan"
    )


class StudentBadge(Base):
    """Junction table: which student earned which badge, and when.

    This table is the source of truth for earned badges; Student.badges_earned
    is a denormalized cache. The unique (student_id, badge_id) constraint
    prevents awarding the same badge twice.
    """

    __tablename__ = "student_badges"
    __table_args__ = (
        UniqueConstraint("student_id", "badge_id", name="uq_student_badge"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    badge_id: Mapped[int] = mapped_column(
        ForeignKey("badges.id", ondelete="CASCADE"), nullable=False
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    student: Mapped["Student"] = relationship(back_populates="student_badges")
    badge: Mapped["Badge"] = relationship(back_populates="student_badges")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class BadgeCreate(BaseModel):
    key: str
    name: str
    description: str | None = None
    icon_url: str | None = None
    criteria_json: dict | None = None


class BadgeRead(BaseModel):
    id: int
    key: str
    name: str
    description: str | None
    icon_url: str | None
    criteria_json: dict | None

    model_config = {"from_attributes": True}


class StudentBadgeRead(BaseModel):
    id: int
    student_id: int
    badge_id: int
    earned_at: datetime

    model_config = {"from_attributes": True}
