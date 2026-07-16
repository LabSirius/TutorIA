from unittest.mock import AsyncMock, MagicMock, patch

from app.config import settings
from app.services.llm_service import OllamaProvider, get_provider


def _mock_completion(content: str = "ok"):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage = MagicMock(prompt_tokens=5, completion_tokens=7)
    return response


async def test_generate_returns_content():
    provider = OllamaProvider()
    with patch.object(
        provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=_mock_completion("Respuesta del LLM"),
    ):
        result = await provider.generate(
            messages=[{"role": "user", "content": "Hola"}],
            system_prompt="Eres TutorIA.",
        )
    assert result == "Respuesta del LLM"


async def test_generate_prepends_system_prompt():
    provider = OllamaProvider()
    with patch.object(
        provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=_mock_completion(),
    ) as create:
        await provider.generate(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="System prompt here",
        )
    messages = create.call_args.kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "System prompt here"}


async def test_generate_model_none_uses_configured_default():
    provider = OllamaProvider()
    with patch.object(
        provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=_mock_completion(),
    ) as create:
        await provider.generate(
            messages=[{"role": "user", "content": "t"}],
            system_prompt="s",
            model=None,
        )
    assert create.call_args.kwargs["model"] == settings.llm_model


async def test_generate_forwards_temperature():
    provider = OllamaProvider()
    with patch.object(
        provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=_mock_completion(),
    ) as create:
        await provider.generate(
            messages=[{"role": "user", "content": "t"}],
            system_prompt="s",
            temperature=0.15,
        )
    assert create.call_args.kwargs["temperature"] == 0.15


def test_get_provider_returns_ollama_and_caches():
    provider = get_provider("ollama")
    assert provider.name == "ollama"
    assert get_provider("ollama") is provider  # cached singleton


def test_get_provider_unknown_raises():
    import pytest

    with pytest.raises(ValueError):
        get_provider("claude")  # not implemented yet
