from unittest.mock import MagicMock, patch

from app.services import rag_service


def test_ingest_and_search():
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["chunk about variables in Python"]],
        "ids": [["mod1_chunk_0"]],
    }

    with patch.object(rag_service, "get_collection", return_value=mock_collection):
        rag_service.ingest_chunks(
            chunks=["chunk about variables in Python"],
            metadatas=[{"module_id": 1}],
            ids=["mod1_chunk_0"],
        )
        mock_collection.upsert.assert_called_once()

        results = rag_service.search_context("qué es una variable", module_id=1)
        assert len(results) == 1
        assert "variables" in results[0]


def test_search_context_returns_empty_on_no_results():
    mock_collection = MagicMock()
    mock_collection.query.return_value = {"documents": [[]], "ids": [[]]}

    with patch.object(rag_service, "get_collection", return_value=mock_collection):
        results = rag_service.search_context("nonexistent topic")
        assert results == []
