import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

LLM_PATCH = "app.services.chat_service.llm_service.get_provider"
GAMIFICATION_PATCH = "app.services.chat_service.gamification_service"


@pytest.fixture(autouse=True)
def _default_student_is_1(monkeypatch):
    # Tests create the default student as id 1; ignore the developer's local .env.
    from app.config import settings

    monkeypatch.setattr(settings, "openedx_default_student_id", 1)


def _mock_llm_provider(reply: str):
    """A stand-in LLM provider whose generate() returns a fixed reply."""
    provider = MagicMock()
    provider.generate = AsyncMock(return_value=reply)
    return provider


class _StreamingProvider:
    """A stand-in LLM provider whose stream() yields fixed tokens and records how far it got."""

    def __init__(self, tokens: list[str], first_delay: float = 0.0, delay: float = 0.0):
        self.tokens = tokens
        self.first_delay = first_delay
        self.delay = delay
        self.yielded = 0
        self.closed = False
        self.generate = AsyncMock()

    async def stream(self, messages, system_prompt, **kwargs):
        try:
            for i, token in enumerate(self.tokens):
                await asyncio.sleep(self.first_delay if i == 0 else self.delay)
                self.yielded += 1
                yield token
        finally:
            self.closed = True


async def _create_student(db, name: str, email: str):
    from app.models.student import Student

    student = Student(name=name, email=email)
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


async def _sessions_of(db, student_id: int):
    from sqlalchemy import select

    from app.models.session import Session

    result = await db.execute(
        select(Session).where(Session.student_id == student_id).execution_options(
            populate_existing=True
        )
    )
    return result.scalars().all()


@pytest.mark.asyncio
async def test_chat_completions_returns_openai_shape(client, db, seeded_prompts):
    # Tables restart identity per test, so this is student 1 (the default).
    student = await _create_student(db, "Ana", "ana@test.com")
    assert student.id == 1

    with patch(LLM_PATCH, return_value=_mock_llm_provider("Hola Ana.")):
        response = await client.post("/v1/chat/completions", json={
            "model": "tutoria",
            "messages": [{"role": "user", "content": "Hola, quiero aprender Python"}],
        })

    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("chatcmpl-")
    assert data["object"] == "chat.completion"
    assert isinstance(data["created"], int)
    assert data["model"] == "tutoria"
    assert data["choices"] == [{
        "index": 0,
        "message": {"role": "assistant", "content": "Hola Ana."},
        "finish_reason": "stop",
    }]
    assert data["usage"] == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


@pytest.mark.asyncio
async def test_chat_completions_reuses_latest_session_and_uses_last_user_message(
    client, db, seeded_prompts
):
    student = await _create_student(db, "Carlos", "carlos@test.com")

    with patch(LLM_PATCH, return_value=_mock_llm_provider("Respuesta del tutor.")):
        await client.post("/v1/chat/completions", json={
            "model": "tutoria",
            "messages": [{"role": "user", "content": "Hola"}],
        })
        # The framework resends its own history; only the last user turn counts.
        await client.post("/v1/chat/completions", json={
            "model": "tutoria",
            "messages": [
                {"role": "system", "content": "Eres un asistente."},
                {"role": "user", "content": "Hola"},
                {"role": "assistant", "content": "Respuesta del tutor."},
                {"role": "user", "content": "Qué es una variable?"},
            ],
        })

    sessions = await _sessions_of(db, student.id)
    assert len(sessions) == 1
    history = sessions[0].message_history
    assert [m["content"] for m in history if m["role"] == "user"] == [
        "Hola", "Qué es una variable?",
    ]
    assert len(history) == 4


@pytest.mark.asyncio
async def test_chat_completions_uses_integer_user_field(client, db, seeded_prompts):
    await _create_student(db, "Default", "default@test.com")
    other = await _create_student(db, "Lucia", "lucia@test.com")

    with patch(LLM_PATCH, return_value=_mock_llm_provider("Hola Lucia.")):
        response = await client.post("/v1/chat/completions", json={
            "model": "tutoria",
            "messages": [{"role": "user", "content": "Hola"}],
            "user": str(other.id),
        })

    assert response.status_code == 200
    assert len(await _sessions_of(db, other.id)) == 1
    assert len(await _sessions_of(db, 1)) == 0


@pytest.mark.asyncio
async def test_chat_completions_non_integer_user_falls_back_to_default(
    client, db, seeded_prompts
):
    student = await _create_student(db, "Ana", "ana@test.com")

    with patch(LLM_PATCH, return_value=_mock_llm_provider("Hola.")):
        response = await client.post("/v1/chat/completions", json={
            "model": "tutoria",
            "messages": [{"role": "user", "content": "Hola"}],
            "user": "edx-username",
        })

    assert response.status_code == 200
    assert response.json()["object"] == "chat.completion"
    assert len(await _sessions_of(db, student.id)) == 1


@pytest.mark.asyncio
async def test_chat_completions_welcome_without_user_message(client, db):
    from sqlalchemy import func, select

    from app.models.session import Session
    from app.models.student import Student
    from app.routers.openai_compat import WELCOME_MESSAGE

    await _create_student(db, "Ana", "ana@test.com")
    provider = _mock_llm_provider("No debería usarse.")

    with patch(LLM_PATCH, return_value=provider), patch(
        "app.routers.openai_compat.process_chat_turn", new_callable=AsyncMock
    ) as chat_turn:
        response = await client.post("/v1/chat/completions", json={
            "model": "tutoria",
            "messages": [
                {"role": "system", "content": "Eres un asistente."},
                {"role": "system", "content": "Contexto del curso."},
            ],
        })

    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("chatcmpl-")
    assert data["object"] == "chat.completion"
    assert data["model"] == "tutoria"
    assert data["choices"] == [{
        "index": 0,
        "message": {"role": "assistant", "content": WELCOME_MESSAGE},
        "finish_reason": "stop",
    }]
    assert WELCOME_MESSAGE == "¡Hola! Soy TutorIA. ¿En qué tema quieres que trabajemos hoy?"
    chat_turn.assert_not_called()
    provider.generate.assert_not_called()
    assert await db.scalar(select(func.count()).select_from(Session)) == 0
    assert await db.scalar(select(func.count()).select_from(Student)) == 1


@pytest.mark.asyncio
async def test_chat_completions_400_for_empty_user_message(client):
    response = await client.post("/v1/chat/completions", json={
        "model": "tutoria",
        "messages": [{"role": "user", "content": "   "}],
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_completions_404_for_missing_student(client):
    response = await client.post("/v1/chat/completions", json={
        "model": "tutoria",
        "messages": [{"role": "user", "content": "Hola"}],
        "user": "999",
    })
    assert response.status_code == 404


def _sse_events(body: str) -> list:
    """Parse an SSE body into decoded JSON chunks, keeping the [DONE] sentinel as-is."""
    import json

    events = []
    for block in body.split("\n\n"):
        if not block:
            continue
        assert block.startswith("data: ")
        payload = block[len("data: "):]
        events.append(payload if payload == "[DONE]" else json.loads(payload))
    return events


def _streamed_content(events: list) -> str:
    return "".join(
        e["choices"][0]["delta"].get("content", "")
        for e in events
        if e != "[DONE]" and e["choices"]
    )


@pytest.mark.asyncio
async def test_chat_completions_stream_forwards_each_token(client, db, seeded_prompts):
    student = await _create_student(db, "Ana", "ana@test.com")
    tokens = ["Hola", " Ana", ".", " Una variable", " guarda", " un valor;\n", "veamos."]
    reply = "".join(tokens)
    provider = _StreamingProvider(tokens)

    with patch(LLM_PATCH, return_value=provider), patch(
        GAMIFICATION_PATCH, new_callable=AsyncMock
    ) as gamification:
        response = await client.post("/v1/chat/completions", json={
            "model": "tutoria",
            "messages": [{"role": "user", "content": "Qué es una variable?"}],
            "stream": True,
        })

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(response.text)

    assert events[-1] == "[DONE]"
    chunks = events[:-1]
    assert chunks[0]["choices"] == [
        {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
    ]
    assert chunks[-1]["choices"] == [{"index": 0, "delta": {}, "finish_reason": "stop"}]
    content_chunks = chunks[1:-1]
    # Each LLM token is its own content chunk, in order.
    assert [c["choices"][0]["delta"] for c in content_chunks] == [
        {"content": t} for t in tokens
    ]
    assert all(c["choices"][0]["finish_reason"] is None for c in content_chunks)

    assert all(c["object"] == "chat.completion.chunk" for c in chunks)
    assert all(c["model"] == "tutoria" for c in chunks)
    assert len({c["id"] for c in chunks}) == 1
    assert chunks[0]["id"].startswith("chatcmpl-")
    assert len({c["created"] for c in chunks}) == 1
    provider.generate.assert_not_called()

    # Persisted once, after generation, with the full reply and its prompt_key.
    sessions = await _sessions_of(db, student.id)
    assert len(sessions) == 1
    user_entry, assistant_entry = sessions[0].message_history
    assert user_entry["role"] == "user"
    assert user_entry["content"] == "Qué es una variable?"
    assert user_entry["prompt_key"] is None
    assert assistant_entry["role"] == "assistant"
    assert assistant_entry["content"] == reply
    assert assistant_entry["prompt_key"]
    assert "interrupted" not in assistant_entry
    gamification.award_xp.assert_awaited_once()
    gamification.update_streak.assert_awaited_once()
    gamification.check_and_award_badges.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_completions_stream_welcome_without_user_message(client, db):
    from sqlalchemy import func, select

    from app.models.session import Session
    from app.routers.openai_compat import WELCOME_MESSAGE

    await _create_student(db, "Ana", "ana@test.com")
    provider = _mock_llm_provider("No debería usarse.")

    with patch(LLM_PATCH, return_value=provider), patch(
        "app.routers.openai_compat.process_chat_turn", new_callable=AsyncMock
    ) as chat_turn, patch("app.routers.openai_compat.stream_chat_turn") as stream_turn:
        response = await client.post("/v1/chat/completions", json={
            "model": "tutoria",
            "messages": [{"role": "system", "content": "Eres un asistente."}],
            "stream": True,
        })

    assert response.status_code == 200
    events = _sse_events(response.text)
    assert events[0]["choices"][0]["delta"] == {"role": "assistant"}
    assert _streamed_content(events) == WELCOME_MESSAGE
    assert events[-2]["choices"][0]["finish_reason"] == "stop"
    assert events[-1] == "[DONE]"
    chat_turn.assert_not_called()
    stream_turn.assert_not_called()
    provider.generate.assert_not_called()
    assert await db.scalar(select(func.count()).select_from(Session)) == 0


@pytest.mark.asyncio
async def test_chat_completions_stream_includes_usage_chunk_when_requested(client):
    response = await client.post("/v1/chat/completions", json={
        "model": "tutoria",
        "messages": [{"role": "system", "content": "Eres un asistente."}],
        "stream": True,
        "stream_options": {"include_usage": True},
    })

    events = _sse_events(response.text)
    assert events[-3]["choices"][0]["finish_reason"] == "stop"
    usage_chunk = events[-2]
    assert usage_chunk["object"] == "chat.completion.chunk"
    assert usage_chunk["id"] == events[0]["id"]
    assert usage_chunk["choices"] == []
    assert usage_chunk["usage"] == {
        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
    }
    assert events[-1] == "[DONE]"


@pytest.mark.asyncio
async def test_chat_completions_stream_reports_errors_in_stream(client):
    from app.routers.openai_compat import STREAM_ERROR_MESSAGE

    response = await client.post("/v1/chat/completions", json={
        "model": "tutoria",
        "messages": [{"role": "user", "content": "Hola"}],
        "user": "999",
        "stream": True,
    })

    # The stream has already started, so the error arrives as content, not as a 404.
    assert response.status_code == 200
    events = _sse_events(response.text)
    assert events[0]["choices"][0]["delta"] == {"role": "assistant"}
    assert _streamed_content(events) == STREAM_ERROR_MESSAGE
    assert events[-2]["choices"][0]["finish_reason"] == "stop"
    assert events[-1] == "[DONE]"


@pytest.mark.asyncio
async def test_chat_completions_stream_400_for_empty_user_message(client):
    response = await client.post("/v1/chat/completions", json={
        "model": "tutoria",
        "messages": [{"role": "user", "content": ""}],
        "stream": True,
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_completions_stream_keepalive_stops_after_first_token(
    client, db, seeded_prompts
):
    await _create_student(db, "Ana", "ana@test.com")
    tokens = ["Hola", " Ana,", " empecemos."]
    reply = "".join(tokens)
    # Slow first token (prompt processing), then gaps longer than the keepalive
    # interval between tokens: keepalives must not reappear once content started.
    provider = _StreamingProvider(tokens, first_delay=0.5, delay=0.2)

    with patch(LLM_PATCH, return_value=provider), patch(
        "app.routers.openai_compat.KEEPALIVE_INTERVAL_SECONDS", 0.05
    ):
        response = await client.post("/v1/chat/completions", json={
            "model": "tutoria",
            "messages": [{"role": "user", "content": "Hola"}],
            "stream": True,
        })

    assert response.status_code == 200
    blocks = [b for b in response.text.split("\n\n") if b]
    keepalives = [i for i, b in enumerate(blocks) if b == ": keepalive"]
    first_content = next(i for i, b in enumerate(blocks) if '"content"' in b)

    assert '"role": "assistant"' in blocks[0]
    assert len(keepalives) >= 2
    # Keepalives only fill the wait between the role chunk and the first token.
    assert all(0 < i < first_content for i in keepalives)
    assert ": keepalive" not in blocks[first_content:]
    data_blocks = [b for b in blocks if b != ": keepalive"]
    assert _streamed_content(_sse_events("\n\n".join(data_blocks) + "\n\n")) == reply
    assert blocks[-1] == "data: [DONE]"


async def _assert_interrupted_turn(db, student_id: int, provider: _StreamingProvider):
    # Generation stopped: the LLM stream was closed and produces nothing more.
    assert provider.closed
    produced = provider.yielded
    assert produced < len(provider.tokens)
    await asyncio.sleep(0.2)
    assert provider.yielded == produced

    sessions = await _sessions_of(db, student_id)
    assert len(sessions) == 1
    user_entry, assistant_entry = sessions[0].message_history
    assert user_entry["content"] == "Hola"
    assert "interrupted" not in user_entry
    assert assistant_entry["role"] == "assistant"
    assert assistant_entry["content"] == "".join(provider.tokens[:produced])
    assert assistant_entry["prompt_key"]
    assert assistant_entry["interrupted"] is True


def _stream_request():
    from app.routers.openai_compat import ChatCompletionRequest

    return ChatCompletionRequest(
        model="tutoria",
        messages=[{"role": "user", "content": "Hola"}],
        stream=True,
    )


@pytest.mark.asyncio
async def test_chat_completions_stream_disconnect_saves_partial_reply(
    client, db, seeded_prompts
):
    """The client leaves after two tokens and the response generator is closed."""
    from app.routers.openai_compat import _stream_completion

    student = await _create_student(db, "Ana", "ana@test.com")
    provider = _StreamingProvider(["Hola", " Ana,", " hoy", " vemos", " variables."], delay=0.05)

    with patch(LLM_PATCH, return_value=provider), patch(
        GAMIFICATION_PATCH, new_callable=AsyncMock
    ) as gamification:
        stream = _stream_completion(_stream_request(), "Hola")
        received = []
        async for event in stream:
            if '"content"' in event:
                received.append(event)
            if len(received) == 2:
                break
        await stream.aclose()

    await _assert_interrupted_turn(db, student.id, provider)
    assert provider.yielded == 2
    gamification.award_xp.assert_not_awaited()
    gamification.update_streak.assert_not_awaited()
    gamification.check_and_award_badges.assert_not_awaited()


@pytest.mark.asyncio
async def test_chat_completions_stream_cancellation_saves_partial_reply(
    client, db, seeded_prompts
):
    """The client leaves while a token is being generated: Starlette cancels the
    response task through an anyio cancel scope (level-triggered cancellation)."""
    import anyio

    from app.routers.openai_compat import _stream_completion

    student = await _create_student(db, "Ana", "ana@test.com")
    provider = _StreamingProvider(["Hola", " Ana,", " hoy", " vemos", " variables."], delay=0.5)
    first_content = anyio.Event()

    async def consume():
        async for event in _stream_completion(_stream_request(), "Hola"):
            if '"content"' in event:
                first_content.set()

    with patch(LLM_PATCH, return_value=provider), patch(
        GAMIFICATION_PATCH, new_callable=AsyncMock
    ) as gamification:
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(consume)
            await first_content.wait()
            task_group.cancel_scope.cancel()

    await _assert_interrupted_turn(db, student.id, provider)
    assert provider.yielded == 1
    gamification.award_xp.assert_not_awaited()
