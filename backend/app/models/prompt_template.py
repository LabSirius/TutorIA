from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------

class PromptTemplate(Base):
    """A pedagogical system prompt, editable and versioned by teachers (RF-21).

    Prompts live in the database (not in .txt files) so the pedagogical team can
    edit, version and audit them from the teacher panel without a code change.
    A partial unique index (on key WHERE is_active) guarantees exactly one
    active prompt per key while still allowing many archived/inactive versions
    to coexist; superseded content is also snapshotted into
    prompt_template_history.
    """

    __tablename__ = "prompt_templates"
    __table_args__ = (
        Index(
            "ux_prompt_templates_active_key",
            "key",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(String(200), default=None)
    updated_by: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    history: Mapped[list["PromptTemplateHistory"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class PromptTemplateHistory(Base):
    """Append-only audit log of every prompt version. Rows are never updated
    or deleted; each edit to a PromptTemplate appends a new snapshot here."""

    __tablename__ = "prompt_template_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_template_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(200), default=None)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    template: Mapped["PromptTemplate"] = relationship(back_populates="history")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class PromptTemplateRead(BaseModel):
    id: int
    key: str
    content: str
    version: int
    is_active: bool
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptTemplateCreate(BaseModel):
    key: str
    content: str = ""
    created_by: str | None = None


class PromptTemplateUpdate(BaseModel):
    content: str
    updated_by: str | None = None
