from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    """Structured metadata stored in content_chunks.metadata (JSONB)."""

    chunk_index: int              # position of this chunk in the source document
    source_length_chars: int      # length of the whole source document
    chunk_length_chars: int       # length of this chunk (including overlap)
    token_count: int              # approximate token count of this chunk
    forced_split: bool            # True if a paragraph had to be broken to fit
    ingested_at: str              # ISO 8601 timestamp of ingestion


class IngestionResult(BaseModel):
    """Summary returned by rag_service.ingest_content."""

    chunks_inserted: int
    total_tokens: int
    avg_chunk_size: float         # average chunk length in characters


class ChunkResult(BaseModel):
    """A single chunk returned by a semantic search, with its cosine distance."""

    chunk_text: str
    distance: float               # cosine distance (0 = identical, 2 = opposite)
    chunk_order: int
    module_id: int
    metadata: ChunkMetadata | None = None
