import logging
from pathlib import Path

import chromadb

from app.config import settings

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(persist_dir))
    return _client


def get_collection() -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name=settings.chroma_collection_name,
    )


def ingest_chunks(
    chunks: list[str],
    metadatas: list[dict],
    ids: list[str],
) -> None:
    collection = get_collection()
    collection.upsert(documents=chunks, metadatas=metadatas, ids=ids)
    logger.info("Ingested %d chunks into collection '%s'", len(chunks), collection.name)


def search_context(
    query: str,
    module_id: int | None = None,
    top_k: int = 3,
) -> list[str]:
    collection = get_collection()
    where_filter = {"module_id": module_id} if module_id else None
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
    )
    documents = results.get("documents")
    if documents and documents[0]:
        return documents[0]
    return []
