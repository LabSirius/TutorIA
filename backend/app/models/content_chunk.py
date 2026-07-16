from datetime import datetime

from pgvector.sqlalchemy import Vector
from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

# Embedding dimension for the RAG index. 768 matches the `nomic-embed-text`
# model served by Ollama. Changing the embedding model means changing this
# value AND re-indexing every chunk (the HNSW index is dimension-specific).
EMBEDDING_DIM = 768


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class ContentChunk(Base):
    """A fragment of curricular module content, indexed for semantic retrieval.

    IMPORTANT — this is Retrieval-Augmented Generation, NOT model training.
    The LLM's weights are never modified. We split curricular text into chunks,
    embed each chunk into a vector, and store the vectors here. At inference
    time the most semantically similar chunks are retrieved and passed to the
    LLM as reference context so its answers stay grounded in the validated
    course material. The model itself remains a fixed, pre-trained artifact.
    """

    __tablename__ = "content_chunks"
    __table_args__ = (
        # Declared here (not only in the migration) so the model stays the single
        # source of truth: otherwise `alembic revision --autogenerate` sees an
        # index it does not know about and emits a DROP for it, silently
        # degrading every semantic search to a sequential scan.
        Index(
            "ix_content_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    # DB column is named "metadata"; the Python attribute is `metadata_json`
    # because `metadata` is reserved by SQLAlchemy's Declarative base.
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ContentChunkRead(BaseModel):
    id: int
    module_id: int
    subject_id: int
    chunk_order: int
    chunk_text: str
    metadata_json: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
