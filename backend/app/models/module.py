from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------

class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    curriculum_version: Mapped[str | None] = mapped_column(String(50), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    modules: Mapped[list["Module"]] = relationship(back_populates="subject")


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    learning_objectives: Mapped[dict | None] = mapped_column(JSON, default=None)
    content_text: Mapped[str | None] = mapped_column(Text, default=None)
    difficulty_level: Mapped[str] = mapped_column(String(20), default="basic")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    subject: Mapped["Subject"] = relationship(back_populates="modules")
    sessions: Mapped[list["Session"]] = relationship(back_populates="module")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="module")
    student_progress: Mapped[list["StudentProgress"]] = relationship(
        back_populates="module"
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SubjectCreate(BaseModel):
    name: str
    description: str | None = None
    curriculum_version: str | None = None


class SubjectRead(BaseModel):
    id: int
    name: str
    description: str | None
    curriculum_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ModuleCreate(BaseModel):
    subject_id: int
    name: str
    order: int = 0
    description: str | None = None
    learning_objectives: dict | None = None
    content_text: str | None = None
    difficulty_level: str = "basic"


class ModuleRead(BaseModel):
    id: int
    subject_id: int
    name: str
    order: int
    description: str | None
    learning_objectives: dict | None
    difficulty_level: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
