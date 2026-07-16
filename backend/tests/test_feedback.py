from app.models.module import Module, Subject
from app.models.student import Student


async def _make_student(db, email="ana@test.com") -> Student:
    student = Student(name="Ana", email=email)
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


# ---------------------------------------------------------------------------
# Feedback events (renamed evaluations CRUD, now under /api/feedback)
# ---------------------------------------------------------------------------

async def test_create_and_get_feedback(client, db):
    subject = Subject(name="Programacion I")
    db.add(subject)
    await db.flush()
    module = Module(subject_id=subject.id, name="Variables")
    db.add(module)
    await db.commit()
    student = await _make_student(db)

    create = await client.post(
        "/api/feedback",
        json={
            "student_id": student.id,
            "module_id": module.id,
            "eval_type": "quiz",
            "questions": {"q1": "¿Qué es una variable?"},
        },
    )
    assert create.status_code == 201
    feedback_id = create.json()["id"]

    fetched = await client.get(f"/api/feedback/{feedback_id}")
    assert fetched.status_code == 200
    assert fetched.json()["eval_type"] == "quiz"

    listed = await client.get("/api/feedback", params={"student_id": student.id})
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_get_feedback_404(client):
    resp = await client.get("/api/feedback/999999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Gamification endpoints
# ---------------------------------------------------------------------------

async def test_award_xp_endpoint(client, db):
    student = await _make_student(db)
    resp = await client.post(
        "/api/feedback/xp",
        json={"student_id": student.id, "amount": 25, "reason": "chat_message"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_id"] == student.id
    assert body["xp_points"] == 25


async def test_award_xp_unknown_student_404(client):
    resp = await client.post(
        "/api/feedback/xp",
        json={"student_id": 999999, "amount": 10, "reason": "x"},
    )
    assert resp.status_code == 404


async def test_get_gamification_endpoint(client, db, seeded_badges):
    student = await _make_student(db, email="carlos@test.com")
    await client.post(
        "/api/feedback/xp",
        json={"student_id": student.id, "amount": 120, "reason": "test"},
    )

    resp = await client.get(f"/api/feedback/gamification/{student.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_id"] == student.id
    assert body["xp_points"] == 120
    assert body["current_streak_days"] == 0
    assert isinstance(body["badges_earned"], list)
