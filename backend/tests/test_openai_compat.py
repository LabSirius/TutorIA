from unittest.mock import AsyncMock, MagicMock, patch

import pytest

LLM_PATCH = "app.services.chat_service.llm_service.get_provider"


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
            "stream": True,
        })

    # stream=True is not supported yet: a full, non-streamed object comes back.
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
