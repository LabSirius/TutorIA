from unittest.mock import AsyncMock, MagicMock, patch

import pytest

LLM_PATCH = "app.services.chat_service.llm_service.get_provider"


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
async def test_chat_completions_stream_emits_openai_chunks(client, db, seeded_prompts):
    student = await _create_student(db, "Ana", "ana@test.com")
    reply = "Hola Ana. Una variable guarda un valor;\nveamos un ejemplo."

    with patch(LLM_PATCH, return_value=_mock_llm_provider(reply)):
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
    assert len(content_chunks) > 1
    assert all(c["choices"][0]["finish_reason"] is None for c in content_chunks)
    assert _streamed_content(events) == reply

    assert all(c["object"] == "chat.completion.chunk" for c in chunks)
    assert all(c["model"] == "tutoria" for c in chunks)
    assert len({c["id"] for c in chunks}) == 1
    assert chunks[0]["id"].startswith("chatcmpl-")
    assert len({c["created"] for c in chunks}) == 1

    # Same pedagogy path as the non-streamed endpoint.
    sessions = await _sessions_of(db, student.id)
    assert len(sessions) == 1
    assert [m["content"] for m in sessions[0].message_history] == [
        "Qué es una variable?", reply,
    ]


@pytest.mark.asyncio
async def test_chat_completions_stream_welcome_without_user_message(client, db):
    from sqlalchemy import func, select

    from app.models.session import Session
    from app.routers.openai_compat import WELCOME_MESSAGE

    await _create_student(db, "Ana", "ana@test.com")
    provider = _mock_llm_provider("No debería usarse.")

    with patch(LLM_PATCH, return_value=provider), patch(
        "app.routers.openai_compat.process_chat_turn", new_callable=AsyncMock
    ) as chat_turn:
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
async def test_chat_completions_stream_sends_keepalive_until_content(
    client, db, seeded_prompts
):
    import asyncio

    await _create_student(db, "Ana", "ana@test.com")
    reply = "Hola Ana, empecemos."

    async def slow_generate(*args, **kwargs):
        await asyncio.sleep(0.5)
        return reply

    provider = MagicMock()
    provider.generate = AsyncMock(side_effect=slow_generate)

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
    # Keepalives only fill the wait between the role chunk and the reply.
    assert all(0 < i < first_content for i in keepalives)
    data_blocks = [b for b in blocks if b != ": keepalive"]
    assert _streamed_content(_sse_events("\n\n".join(data_blocks) + "\n\n")) == reply
    assert blocks[-1] == "data: [DONE]"
