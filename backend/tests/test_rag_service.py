import pytest
from sqlalchemy.dialects import postgresql

from app.services import chunking, rag_service
from app.services.chunking import MAX_CHARS, OVERLAP_CHARS, chunk_text, count_tokens
from app.services.embedding_client import EmbeddingError


# ---------------------------------------------------------------------------
# Unit tests — chunking (pure, no DB, no Ollama)
# ---------------------------------------------------------------------------

def test_count_tokens_approximation():
    assert count_tokens("") == 0
    assert count_tokens("a" * 4) == 1
    assert count_tokens("a" * 5) == 2  # 5 chars / 4 -> rounded up


def test_chunk_text_preserves_small_paragraphs():
    text = "Primer parrafo sobre variables.\n\nSegundo parrafo sobre bucles."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert "variables" in chunks[0].text and "bucles" in chunks[0].text
    assert chunks[0].forced_split is False


def test_chunk_text_respects_max_size():
    paragraph = ("palabra " * 60).strip()  # ~480 chars, under MAX
    text = "\n\n".join(f"[P{i}] {paragraph}" for i in range(12))
    chunks = chunk_text(text)
    assert len(chunks) > 1
    # Each chunk stays within the budget plus at most one overlap prefix.
    for chunk in chunks:
        assert len(chunk.text) <= MAX_CHARS + OVERLAP_CHARS + 5


def test_chunk_text_applies_overlap():
    paragraph = ("dato " * 80).strip()  # ~400 chars
    text = "\n\n".join(f"P{i} {paragraph}" for i in range(10))
    chunks = chunk_text(text)
    assert len(chunks) >= 2
    # The start of chunk 2 should reproduce a slice from the tail of chunk 1.
    tail = chunks[0].text[-OVERLAP_CHARS:].strip().split()
    assert any(word in chunks[1].text[:OVERLAP_CHARS + 20] for word in tail[-3:])


def test_chunk_text_flags_forced_split_on_giant_paragraph():
    giant = "concepto " * 600  # ~5400 chars, single paragraph, no blank lines
    chunks = chunk_text(giant)
    assert len(chunks) > 1
    assert any(chunk.forced_split for chunk in chunks)


def test_chunk_text_empty_returns_nothing():
    assert chunk_text("   \n\n  ") == []


# ---------------------------------------------------------------------------
# Unit tests — search query construction
# ---------------------------------------------------------------------------

def test_build_search_stmt_uses_cosine_operator():
    stmt = rag_service._build_search_stmt([0.1] * 768, module_id=7, top_k=3)
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "<=>" in sql                      # cosine distance operator (index-friendly)
    assert "content_chunks.module_id" in sql
    assert "ORDER BY" in sql.upper()
    assert "LIMIT" in sql.upper()


# ---------------------------------------------------------------------------
# Unit tests — transactional ingestion (embedding mocked)
# ---------------------------------------------------------------------------

async def test_ingest_empty_text_makes_no_calls(monkeypatch):
    calls = {"embed": 0}

    async def fake_embed_batch(texts):
        calls["embed"] += 1
        return []

    monkeypatch.setattr(rag_service.embedding_client, "embed_batch", fake_embed_batch)
    result = await rag_service.ingest_content(module_id=1, text="   ")
    assert result.chunks_inserted == 0
    assert calls["embed"] == 0  # empty text short-circuits before embedding


async def test_ingest_aborts_on_embedding_failure_without_db_writes(monkeypatch):
    async def failing_embed_batch(texts):
        raise EmbeddingError("ollama unreachable")

    monkeypatch.setattr(rag_service.embedding_client, "embed_batch", failing_embed_batch)

    # If the DB session were opened, this sentinel would be called — it must not be.
    class ExplodingSessionmaker:
        def __call__(self, *args, **kwargs):
            raise AssertionError("database session must not be opened on embed failure")

    monkeypatch.setattr(rag_service.database, "async_session", ExplodingSessionmaker())

    with pytest.raises(EmbeddingError):
        await rag_service.ingest_content(module_id=1, text="algo\n\notra cosa")


# ---------------------------------------------------------------------------
# Integration test — real Ollama + real Postgres (skipped if Ollama absent)
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_ingest_and_search_roundtrip(db, ollama_available):
    from app.models.module import Module, Subject

    subject = Subject(name="Programacion I")
    db.add(subject)
    await db.flush()
    module = Module(subject_id=subject.id, name="Variables")
    db.add(module)
    await db.commit()

    text = (
        "Una variable en Python es un contenedor que guarda un valor.\n\n"
        "Un bucle for repite un bloque de instrucciones un numero de veces.\n\n"
        "Una funcion agrupa instrucciones reutilizables bajo un nombre."
    )
    result = await rag_service.ingest_content(module.id, text)
    assert result.chunks_inserted > 0

    hits = await rag_service.search_context(
        "que es una variable", module_id=module.id, top_k=3
    )
    assert hits
    assert any("variable" in hit.chunk_text.lower() for hit in hits)
