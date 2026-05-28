from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import llm_service


@pytest.mark.asyncio
async def test_send_message_returns_content():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Respuesta del LLM"
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

    with patch.object(
        llm_service.client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await llm_service.send_message(
            messages=[{"role": "user", "content": "Hola"}],
            system_prompt="Eres TutorIA.",
        )

    assert result == "Respuesta del LLM"


@pytest.mark.asyncio
async def test_send_message_prepends_system_prompt():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"
    mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=5)

    with patch.object(
        llm_service.client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_create:
        await llm_service.send_message(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="System prompt here",
        )

        call_kwargs = mock_create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "System prompt here"
