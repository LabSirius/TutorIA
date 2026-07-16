"""Request routing between LLM providers.

Placeholder infrastructure: the intelligent classifier is a future-phase feature
(RF-23). For now every request is routed to the local Ollama provider.
"""
import logging
from typing import Literal

logger = logging.getLogger(__name__)

Provider = Literal["ollama", "claude"]


class RequestRouter:
    """Decides which LLM provider should handle a given request."""

    async def choose_provider(
        self, user_message: str, student_context: dict
    ) -> Provider:
        # TODO(RF-23): when USE_CLASSIFIER is enabled and CLAUDE_API_KEY is set,
        # call a lightweight Haiku classifier here to route complex queries to
        # Claude API and keep simple ones on the local Ollama model (cost
        # optimization). Until that future phase, everything runs locally.
        return "ollama"


# Module-level singleton used by the chat router.
request_router = RequestRouter()
