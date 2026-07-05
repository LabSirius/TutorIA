"""RAG pipeline backed by PostgreSQL + pgvector.

IMPORTANT — this module performs retrieval, NOT model training. Curricular text
is chunked, embedded with a pre-trained model (via Ollama) and stored as vectors
in the content_chunks table. At query time we retrieve the most semantically
similar chunks and hand them to the LLM as reference context. The LLM's weights
are never touched; the model stays a fixed, pre-trained artifact.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db import database
from app.models.content_chunk import ContentChunk
from app.models.module import Module
from app.schemas.rag import ChunkMetadata, ChunkResult, IngestionResult
from app.services.chunking import chunk_text, count_tokens
from app.services.embedding_client import EmbeddingClient

logger = logging.getLogger(__name__)

# Module-level client so tests can patch rag_service.embedding_client.
embedding_client = EmbeddingClient()


def _build_search_stmt(query_embedding: list[float], module_id: int, top_k: int):
    """Build the nearest-neighbour query. Ordering by cosine distance (`<=>`,
    via cosine_distance) is what lets PostgreSQL use the HNSW index that was
    created with vector_cosine_ops."""
    distance = ContentChunk.embedding.cosine_distance(query_embedding)
    return (
        select(ContentChunk, distance.label("distance"))
        .where(ContentChunk.module_id == module_id)
        .order_by(distance)
        .limit(top_k)
    )


async def ingest_content(module_id: int, text: str) -> IngestionResult:
    """Chunk, embed and store a module's content as a single transactional unit.

    Embeddings are generated BEFORE any database write; if any embedding fails
    the function raises and the database is never touched (no partial inserts).
    Re-ingesting a module replaces its existing chunks atomically.
    """
    chunks = chunk_text(text)
    if not chunks:
        return IngestionResult(chunks_inserted=0, total_tokens=0, avg_chunk_size=0.0)

    # Embeddings first — a failure here aborts before we open a transaction.
    embeddings = await embedding_client.embed_batch([c.text for c in chunks])

    source_length = len(text)
    ingested_at = datetime.now(timezone.utc).isoformat()
    prepared: list[tuple[int, str, list[float], dict]] = []
    total_tokens = 0
    total_chars = 0
    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        tokens = count_tokens(chunk.text)
        total_tokens += tokens
        total_chars += len(chunk.text)
        metadata = ChunkMetadata(
            chunk_index=index,
            source_length_chars=source_length,
            chunk_length_chars=len(chunk.text),
            token_count=tokens,
            forced_split=chunk.forced_split,
            ingested_at=ingested_at,
        )
        prepared.append((index, chunk.text, embedding, metadata.model_dump()))

    # Single transaction: replace this module's chunks atomically.
    async with database.async_session() as session:
        async with session.begin():
            module = await session.get(Module, module_id)
            if module is None:
                raise ValueError(
                    f"Module {module_id} not found; cannot ingest content"
                )
            await session.execute(
                delete(ContentChunk).where(ContentChunk.module_id == module_id)
            )
            session.add_all(
                [
                    ContentChunk(
                        module_id=module_id,
                        subject_id=module.subject_id,
                        chunk_order=index,
                        chunk_text=chunk_text_value,
                        embedding=embedding,
                        metadata_json=metadata,
                    )
                    for index, chunk_text_value, embedding, metadata in prepared
                ]
            )

    logger.info(
        "Ingested %d chunks for module %d (%d tokens)",
        len(prepared), module_id, total_tokens,
    )
    return IngestionResult(
        chunks_inserted=len(prepared),
        total_tokens=total_tokens,
        avg_chunk_size=round(total_chars / len(prepared), 2),
    )


async def search_context(
    query: str, module_id: int, top_k: int = 3
) -> list[ChunkResult]:
    """Return the top_k chunks of a module most semantically similar to query."""
    query_embedding = await embedding_client.embed(query)
    stmt = _build_search_stmt(query_embedding, module_id, top_k)

    async with database.async_session() as session:
        rows = (await session.execute(stmt)).all()

    results: list[ChunkResult] = []
    for chunk, distance in rows:
        metadata = None
        if chunk.metadata_json:
            try:
                metadata = ChunkMetadata(**chunk.metadata_json)
            except (TypeError, ValueError):
                metadata = None  # tolerate legacy/partial metadata
        results.append(
            ChunkResult(
                chunk_text=chunk.chunk_text,
                distance=float(distance),
                chunk_order=chunk.chunk_order,
                module_id=chunk.module_id,
                metadata=metadata,
            )
        )
    return results


async def delete_module_content(module_id: int) -> int:
    """Delete all chunks for a module. Returns the number of rows deleted."""
    async with database.async_session() as session:
        async with session.begin():
            result = await session.execute(
                delete(ContentChunk).where(ContentChunk.module_id == module_id)
            )
        return result.rowcount or 0
