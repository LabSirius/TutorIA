from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_chat_creates_session_and_returns_response(client, db):
    from app.models.student import Student

    student = Student(name="Ana", email="ana@test.com")
    db.add(student)
    await db.commit()
    await db.refresh(student)

    mock_reply = "Hola Ana, bienvenida a TutorIA."

    with patch("app.routers.chat.llm_service.send_message", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_reply
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
async def test_chat_continues_existing_session(client, db):
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

    with patch("app.routers.chat.llm_service.send_message", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Las variables son como cajas."
        response = await client.post("/api/chat", json={
            "student_id": student.id,
            "message": "Qué es una variable?",
            "session_id": session.id,
        })

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session.id
    assert data["prompt_type_used"] != "diagnostic"
