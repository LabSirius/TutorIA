"""Async client for Ollama's native embeddings endpoint (POST /api/embeddings).

NOTE: generating embeddings is NOT model training. We send curricular text to a
pre-trained embedding model and store the returned vectors for semantic search.
The model's parameters are never modified.
"""
import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Embedding generation failed (network, timeout, or malformed response)."""


class EmbeddingModelUnavailableError(EmbeddingError):
    """Ollama is unreachable or the embedding model has not been pulled."""


class EmbeddingClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int = 3,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.embedding_model
        self.timeout = timeout or settings.embedding_timeout
        self.max_retries = max_retries

    async def _request_embedding(self, text: str) -> list[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": self.model, "prompt": text}
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)

                if response.status_code == 404 or (
                    response.status_code >= 400
                    and "not found" in response.text.lower()
                ):
                    raise EmbeddingModelUnavailableError(
                        f"Embedding model '{self.model}' is not available in Ollama "
                        f"at {self.base_url}. Pull it with:  "
                        f"ollama pull {self.model}"
                    )
                response.raise_for_status()
                embedding = response.json().get("embedding")
                if not embedding:
                    raise EmbeddingError(
                        f"Ollama returned an empty embedding for model '{self.model}'"
                    )
                return embedding
            except EmbeddingModelUnavailableError:
                raise  # a missing model will not fix itself on retry
            except (httpx.HTTPError, EmbeddingError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    backoff = 0.5 * (2 ** (attempt - 1))
                    logger.warning(
                        "Embedding attempt %d/%d failed: %s; retrying in %.1fs",
                        attempt, self.max_retries, exc, backoff,
                    )
                    await asyncio.sleep(backoff)

        raise EmbeddingError(
            f"Failed to generate embedding after {self.max_retries} attempts: {last_exc}"
        )

    async def embed(self, text: str) -> list[float]:
        return await self._request_embedding(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Sequential requests keep memory/GPU pressure low on the shared,
        # resource-constrained Ollama server.
        return [await self._request_embedding(text) for text in texts]

    async def verify_available(self) -> None:
        """Startup check: raise EmbeddingModelUnavailableError if Ollama is
        unreachable or the embedding model has not been pulled."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise EmbeddingModelUnavailableError(
                f"Cannot reach Ollama at {self.base_url} to verify the embedding "
                f"model '{self.model}'. Is Ollama running? ({exc})"
            ) from exc

        available = {m.get("name", "").split(":")[0] for m in payload.get("models", [])}
        if self.model.split(":")[0] not in available:
            raise EmbeddingModelUnavailableError(
                f"Embedding model '{self.model}' is not pulled in Ollama at "
                f"{self.base_url}. Pull it with:  ollama pull {self.model}"
            )
