from datetime import datetime, timezone

from app.models.module import Module, Subject
from app.models.session import Session
from app.models.student import Student
from app.models.teacher import Teacher, TeacherCourse


async def _setup_course_with_teacher(db):
    subject = Subject(name="Programacion I")
    db.add(subject)
    await db.flush()
    module = Module(subject_id=subject.id, name="Variables")
    db.add(module)
    await db.flush()
    teacher = Teacher(name="Prof. Ramirez", email="ramirez@utp.edu.co")
    db.add(teacher)
    await db.flush()
    db.add(TeacherCourse(teacher_id=teacher.id, subject_id=subject.id, role="owner"))
    student = Student(name="Ana", email="ana@test.com")
    db.add(student)
    await db.flush()
    await db.commit()
    return subject, module, teacher, student


async def test_conversations_endpoint_returns_student_sessions(client, db):
    subject, module, teacher, student = await _setup_course_with_teacher(db)
    db.add(
        Session(
            student_id=student.id,
            module_id=module.id,
            started_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 3, 1, 10, 30, tzinfo=timezone.utc),
            message_history=[
                {"role": "user", "content": "hola", "timestamp": "t1", "prompt_key": None},
                {"role": "assistant", "content": "buenas", "timestamp": "t2", "prompt_key": "diagnostic"},
            ],
        )
    )
    await db.commit()

    resp = await client.get(
        f"/api/analytics/student/{student.id}/conversations",
        headers={"X-Teacher-Id": str(teacher.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["has_more"] is False

    item = body["items"][0]
    assert item["module_name"] == "Variables"
    assert item["subject_name"] == "Programacion I"
    assert item["subject_id"] == subject.id
    assert item["message_count"] == 2
    assert item["duration_minutes"] == 30.0


async def test_conversations_endpoint_paginates_correctly(client, db):
    subject, module, teacher, student = await _setup_course_with_teacher(db)
    for hour in range(5):
        db.add(
            Session(
                student_id=student.id,
                module_id=module.id,
                started_at=datetime(2026, 3, 1, 10 + hour, 0, tzinfo=timezone.utc),
                message_history=[{"role": "user", "content": "x", "timestamp": "t"}],
            )
        )
    await db.commit()

    page1 = await client.get(
        f"/api/analytics/student/{student.id}/conversations",
        params={"page": 1, "page_size": 2},
        headers={"X-Teacher-Id": str(teacher.id)},
    )
    assert page1.status_code == 200
    body1 = page1.json()
    assert body1["total"] == 5
    assert len(body1["items"]) == 2
    assert body1["has_more"] is True

    page3 = await client.get(
        f"/api/analytics/student/{student.id}/conversations",
        params={"page": 3, "page_size": 2},
        headers={"X-Teacher-Id": str(teacher.id)},
    )
    body3 = page3.json()
    assert len(body3["items"]) == 1
    assert body3["has_more"] is False

    # Pages must not overlap (ordered by started_at desc).
    ids_page1 = {i["session_id"] for i in body1["items"]}
    ids_page3 = {i["session_id"] for i in body3["items"]}
    assert not (ids_page1 & ids_page3)


async def test_transcript_endpoint_returns_full_history_with_prompt_keys(client, db):
    subject, module, teacher, student = await _setup_course_with_teacher(db)
    session = Session(
        student_id=student.id,
        module_id=module.id,
        started_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        message_history=[
            {"role": "user", "content": "¿Qué es una variable?", "timestamp": "t1", "prompt_key": None},
            {"role": "assistant", "content": "Pensemos juntos...", "timestamp": "t2", "prompt_key": "socratic"},
        ],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    resp = await client.get(
        f"/api/analytics/session/{session.id}/transcript",
        headers={"X-Teacher-Id": str(teacher.id)},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["session_metadata"]["session_id"] == session.id
    assert body["session_metadata"]["student_id"] == student.id
    assert body["session_metadata"]["subject_id"] == subject.id

    messages = body["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["prompt_key"] is None
    assert messages[1]["role"] == "assistant"
    assert messages[1]["prompt_key"] == "socratic"  # strategy traceability


async def test_conversations_endpoint_returns_403_for_unauthorized_teacher(client, db):
    subject, module, teacher, student = await _setup_course_with_teacher(db)
    db.add(Session(student_id=student.id, module_id=module.id))
    # A teacher with no assignment to this student's subject.
    other = Teacher(name="Prof. Ajeno", email="ajeno@utp.edu.co")
    db.add(other)
    await db.flush()
    await db.commit()

    resp = await client.get(
        f"/api/analytics/student/{student.id}/conversations",
        headers={"X-Teacher-Id": str(other.id)},
    )
    assert resp.status_code == 403


async def test_transcript_endpoint_returns_404_for_missing_session(client, db):
    _, _, teacher, _ = await _setup_course_with_teacher(db)
    resp = await client.get(
        "/api/analytics/session/999999/transcript",
        headers={"X-Teacher-Id": str(teacher.id)},
    )
    assert resp.status_code == 404
