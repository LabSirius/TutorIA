from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_llm_provider(reply: str):
    """A stand-in LLM provider whose generate() returns a fixed reply."""
    provider = MagicMock()
    provider.generate = AsyncMock(return_value=reply)
    return provider


@pytest.mark.asyncio
async def test_chat_creates_session_and_returns_response(client, db, seeded_prompts):
    from app.models.student import Student

    student = Student(name="Ana", email="ana@test.com")
    db.add(student)
    await db.commit()
    await db.refresh(student)

    mock_reply = "Hola Ana, bienvenida a TutorIA."

    with patch(
        "app.services.chat_service.llm_service.get_provider",
        return_value=_mock_llm_provider(mock_reply),
    ):
        response = await client.post("/api/chat", json={
            "student_id": student.id,
            "message": "Hola, quiero aprender Python",
        })

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == mock_reply
    assert "session_id" in data
    assert data["prompt_type_used"] == "diagnostic"


@pytest.mark.asyncio
async def test_chat_returns_404_for_missing_student(client):
    response = await client.post("/api/chat", json={
        "student_id": 999,
        "message": "Hola",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_continues_existing_session(client, db, seeded_prompts):
    from app.models.session import Session
    from app.models.student import Student

    student = Student(name="Carlos", email="carlos@test.com")
    db.add(student)
    await db.commit()
    await db.refresh(student)

    session = Session(
        student_id=student.id,
        message_history=[
            {"role": "user", "content": "Hola", "timestamp": "2026-01-01T00:00:00Z"},
            {"role": "assistant", "content": "Hola Carlos", "timestamp": "2026-01-01T00:00:01Z"},
        ],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    with patch(
        "app.services.chat_service.llm_service.get_provider",
        return_value=_mock_llm_provider("Las variables son como cajas."),
    ):
        response = await client.post("/api/chat", json={
            "student_id": student.id,
            "message": "Qué es una variable?",
            "session_id": session.id,
        })

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session.id
    assert data["prompt_type_used"] != "diagnostic"


@pytest.mark.asyncio
async def test_chat_persists_all_turns_on_continued_session(client, db, seeded_prompts):
    from app.models.session import Session
    from app.models.student import Student

    student = Student(name="Lucia", email="lucia@test.com")
    db.add(student)
    await db.commit()
    await db.refresh(student)

    with patch(
        "app.services.chat_service.llm_service.get_provider",
        return_value=_mock_llm_provider("Respuesta del tutor."),
    ):
        first = await client.post("/api/chat", json={
            "student_id": student.id,
            "message": "Hola, quiero aprender Python",
        })
        session_id = first.json()["session_id"]
        second = await client.post("/api/chat", json={
            "student_id": student.id,
            "message": "Qué es una variable?",
            "session_id": session_id,
        })

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["session_id"] == session_id

    session = await db.get(Session, session_id)
    await db.refresh(session)
    assert len(session.message_history) == 4
    assert [m["role"] for m in session.message_history] == [
        "user", "assistant", "user", "assistant",
    ]
