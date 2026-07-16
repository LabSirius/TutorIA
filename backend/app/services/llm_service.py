"""LLM provider layer.

Today TutorIA runs a single local provider (Ollama, via its OpenAI-compatible
API). This module is structured so that adding Claude API in a future phase is
a new provider class + one line in `get_provider` + configuration — with no
change to callers. Providers all expose the same `generate(...)` coroutine, so
the router (router_service) can pick one by name without callers caring how it
is implemented. See RF-23.
"""
import logging
import time

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaProvider:
    """LLM provider backed by an OpenAI-compatible endpoint (Ollama).

    A future ClaudeProvider will expose the SAME `generate` signature, so
    callers (the chat router) never need to change when a provider is added.
    """

    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        default_model: str | None = None,
    ):
        self._client = AsyncOpenAI(
            base_url=base_url or settings.llm_base_url,
            api_key=api_key or settings.llm_api_key,
        )
        self.default_model = default_model or settings.llm_model

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a completion. `model=None` uses the provider's configured
        default model."""
        full_messages = [{"role": "system", "content": system_prompt}, *messages]
        chosen_model = model or self.default_model
        tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

        start = time.monotonic()
        response = await self._client.chat.completions.create(
            model=chosen_model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=tokens,
        )
        elapsed = time.monotonic() - start

        usage = response.usage
        logger.info(
            "LLM request: provider=%s model=%s tokens_in=%s tokens_out=%s latency=%.2fs",
            self.name,
            chosen_model,
            usage.prompt_tokens if usage else "?",
            usage.completion_tokens if usage else "?",
            elapsed,
        )
        return response.choices[0].message.content

    async def stream(
        self,
        messages: list[dict],
        system_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ):
        """Stream a completion token-by-token."""
        full_messages = [{"role": "system", "content": system_prompt}, *messages]
        chosen_model = model or self.default_model
        tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

        stream = await self._client.chat.completions.create(
            model=chosen_model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


# Provider registry. Instances are cached so the underlying HTTP clients are
# reused across requests.
_providers: dict[str, OllamaProvider] = {}


def get_provider(name: str = "ollama") -> OllamaProvider:
    """Return the LLM provider for `name`. Currently only 'ollama' exists; a
    future phase adds 'claude' here (RF-23) without changing callers."""
    if name not in _providers:
        if name == "ollama":
            _providers[name] = OllamaProvider()
        else:
            # Future: elif name == "claude": _providers[name] = ClaudeProvider()
            raise ValueError(f"LLM provider '{name}' is not implemented yet")
    return _providers[name]
