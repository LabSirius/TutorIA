from datetime import datetime, timezone

import pytest

from app.models.gamification import Badge, StudentBadge
from app.models.module import Module, Subject
from app.models.session import Session
from app.models.student import Student, StudentProgress
from app.services import gamification_service


async def _make_student(db, **kwargs) -> Student:
    student = Student(
        name=kwargs.pop("name", "Ana"),
        email=kwargs.pop("email", "ana@test.com"),
        **kwargs,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


# ---------------------------------------------------------------------------
# award_xp
# ---------------------------------------------------------------------------

async def test_award_xp_increments_and_returns_total(db):
    student = await _make_student(db)
    assert await gamification_service.award_xp(student.id, 30, "chat_message") == 30
    assert await gamification_service.award_xp(student.id, 15, "correct_answer") == 45
    await db.refresh(student)
    assert student.xp_points == 45


async def test_award_xp_unknown_student_raises(db):
    with pytest.raises(ValueError):
        await gamification_service.award_xp(999999, 10, "x")


# ---------------------------------------------------------------------------
# check_and_award_badges — one test per criteria type
# ---------------------------------------------------------------------------

async def test_award_xp_threshold_badge(db, seeded_badges):
    student = await _make_student(db, xp_points=120)
    awarded = await gamification_service.check_and_award_badges(student.id)
    assert set(awarded) == {"xp_100"}
    # Idempotent: a second evaluation does not re-award.
    assert "xp_100" not in await gamification_service.check_and_award_badges(student.id)


async def test_award_streak_badge(db, seeded_badges):
    student = await _make_student(db, current_streak_days=7)
    awarded = await gamification_service.check_and_award_badges(student.id)
    assert "streak_7_days" in awarded


async def test_award_modules_completed_badge(db, seeded_badges):
    subject = Subject(name="Programacion I")
    db.add(subject)
    await db.flush()
    module = Module(subject_id=subject.id, name="Variables")
    db.add(module)
    await db.flush()
    student = await _make_student(db)
    db.add(
        StudentProgress(
            student_id=student.id, module_id=module.id, module_level="completed"
        )
    )
    await db.commit()

    awarded = await gamification_service.check_and_award_badges(student.id)
    assert "first_module_completed" in awarded


async def test_award_first_message_badge(db, seeded_badges):
    student = await _make_student(db)
    db.add(
        Session(
            student_id=student.id,
            message_history=[{"role": "user", "content": "hola", "timestamp": "t"}],
        )
    )
    await db.commit()

    awarded = await gamification_service.check_and_award_badges(student.id)
    assert "first_message" in awarded


async def test_award_night_owl_badge(db, seeded_badges):
    student = await _make_student(db)
    late = datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)
    db.add(
        Session(
            student_id=student.id,
            started_at=late,
            message_history=[{"role": "user", "content": "x", "timestamp": "t"}],
        )
    )
    await db.commit()

    awarded = await gamification_service.check_and_award_badges(student.id)
    assert "night_owl" in awarded


async def test_no_badges_when_nothing_qualifies(db, seeded_badges):
    student = await _make_student(db)  # fresh student, no activity, 0 xp
    assert await gamification_service.check_and_award_badges(student.id) == []


# ---------------------------------------------------------------------------
# update_streak edge cases
# ---------------------------------------------------------------------------

async def test_update_streak_first_session_is_one(db):
    student = await _make_student(db)
    db.add(
        Session(
            student_id=student.id,
            started_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        )
    )
    await db.commit()
    assert await gamification_service.update_streak(student.id) == 1


async def test_update_streak_new_day_within_window_increments(db):
    student = await _make_student(db, current_streak_days=3)
    db.add(
        Session(
            student_id=student.id,
            started_at=datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc),
        )
    )
    db.add(
        Session(
            student_id=student.id,
            started_at=datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc),  # +12h, next day
        )
    )
    await db.commit()
    assert await gamification_service.update_streak(student.id) == 4


async def test_update_streak_window_exceeded_resets(db):
    student = await _make_student(db, current_streak_days=5)
    db.add(
        Session(
            student_id=student.id,
            started_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
        )
    )
    db.add(
        Session(
            student_id=student.id,
            started_at=datetime(2026, 1, 3, 8, 0, tzinfo=timezone.utc),  # +48h > 36h window
        )
    )
    await db.commit()
    assert await gamification_service.update_streak(student.id) == 1


# ---------------------------------------------------------------------------
# get_gamification_state
# ---------------------------------------------------------------------------

async def test_get_gamification_state(db, seeded_badges):
    student = await _make_student(db, xp_points=120)
    await gamification_service.check_and_award_badges(student.id)

    state = await gamification_service.get_gamification_state(student.id)
    assert state["xp_points"] == 120
    assert state["current_streak_days"] == 0
    assert "xp_100" in state["badges_earned"]
