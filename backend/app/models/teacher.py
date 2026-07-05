from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------

class Teacher(Base):
    """A teacher who monitors students and manages curricular content/prompts.

    Mirrors the basic shape of Student. Used for the teacher panel and for the
    conversation-traceability authorization checks (a teacher may only view the
    students enrolled in a subject they are assigned to via teacher_courses).
    """

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    courses: Mapped[list["TeacherCourse"]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )


class TeacherCourse(Base):
    """Assignment of a teacher to a subject, with a role. Composite PK
    (teacher_id, subject_id): a teacher holds a single role per subject."""

    __tablename__ = "teacher_courses"
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'co_teacher')", name="ck_teacher_course_role"
        ),
    )

    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), primary_key=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="owner")

    teacher: Mapped["Teacher"] = relationship(back_populates="courses")
    subject: Mapped["Subject"] = relationship(back_populates="teacher_courses")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class TeacherCreate(BaseModel):
    name: str
    email: str


class TeacherRead(BaseModel):
    id: int
    name: str
    email: str
    registered_at: datetime

    model_config = {"from_attributes": True}


class TeacherCourseCreate(BaseModel):
    teacher_id: int
    subject_id: int
    role: str = "owner"


class TeacherCourseRead(BaseModel):
    teacher_id: int
    subject_id: int
    role: str

    model_config = {"from_attributes": True}
