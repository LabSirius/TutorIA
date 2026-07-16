"""Gamification service (RF-16, RF-24).

The mechanics implemented here are PROVISIONAL placeholders to enable end-to-end
testing. The tunable numbers live in config.py (gamification_* settings) and the
badge rules live in badges.criteria_json — NOT hard-coded here — so the
pedagogical team can finalize them without touching this code.
"""
import logging
from datetime import datetime

from sqlalchemy import func, select

from app.config import settings
from app.db import database
from app.models.gamification import Badge, StudentBadge
from app.models.session import Session
from app.models.student import Student, StudentProgress

logger = logging.getLogger(__name__)


async def award_xp(student_id: int, amount: int, reason: str) -> int:
    """Add XP to a student. Returns the new total XP."""
    async with database.async_session() as session:
        async with session.begin():
            student = await session.get(Student, student_id)
            if student is None:
                raise ValueError(f"Student {student_id} not found")
            student.xp_points = (student.xp_points or 0) + amount
            new_total = student.xp_points
    logger.info(
        "Awarded %d XP to student %d (reason=%s); new total=%d",
        amount, student_id, reason, new_total,
    )
    return new_total


def _is_late_night(moment: datetime) -> bool:
    # PROVISIONAL (RF-24): "late night" = 22:00-04:59. The timezone policy (server
    # vs. Colombia local) will be finalized with the pedagogical team.
    return moment.hour >= 22 or moment.hour < 5


def _badge_qualifies(
    criteria: dict,
    *,
    xp: int,
    streak: int,
    modules_completed: int,
    has_any_message: bool,
    has_late_night_session: bool,
) -> bool:
    """Interpret a badge's criteria_json against the student's current state."""
    criteria_type = criteria.get("type")
    threshold = criteria.get("threshold", 0)

    if criteria_type == "xp_threshold":
        return xp >= threshold
    if criteria_type == "streak_days":
        return streak >= threshold
    if criteria_type == "modules_completed":
        return modules_completed >= threshold
    if criteria_type == "first_time_action":
        action_key = criteria.get("action_key", "first_message")
        if action_key == "first_message":
            return has_any_message
        if action_key == "late_night_session":
            return has_late_night_session
        return False
    return False


async def check_and_award_badges(student_id: int) -> list[str]:
    """Evaluate every badge rule against the student's current state, award any
    newly-earned badges, and return the list of badge keys awarded in this call."""
    async with database.async_session() as session:
        async with session.begin():
            student = await session.get(Student, student_id)
            if student is None:
                raise ValueError(f"Student {student_id} not found")

            badges = (await session.execute(select(Badge))).scalars().all()
            earned_keys = set(
                (
                    await session.execute(
                        select(Badge.key)
                        .join(StudentBadge, StudentBadge.badge_id == Badge.id)
                        .where(StudentBadge.student_id == student_id)
                    )
                ).scalars().all()
            )
            modules_completed = (
                await session.execute(
                    select(func.count())
                    .select_from(StudentProgress)
                    .where(StudentProgress.student_id == student_id)
                    .where(StudentProgress.module_level == "completed")
                )
            ).scalar() or 0
            sessions = (
                await session.execute(
                    select(Session).where(Session.student_id == student_id)
                )
            ).scalars().all()
            has_any_message = any(s.message_history for s in sessions)
            has_late_night_session = any(
                _is_late_night(s.started_at) for s in sessions if s.started_at
            )

            awarded: list[str] = []
            for badge in badges:
                if badge.key in earned_keys:
                    continue
                if _badge_qualifies(
                    badge.criteria_json or {},
                    xp=student.xp_points or 0,
                    streak=student.current_streak_days or 0,
                    modules_completed=modules_completed,
                    has_any_message=has_any_message,
                    has_late_night_session=has_late_night_session,
                ):
                    session.add(
                        StudentBadge(student_id=student_id, badge_id=badge.id)
                    )
                    awarded.append(badge.key)

            if awarded:
                student.badges_earned = list(student.badges_earned or []) + awarded

    if awarded:
        logger.info("Student %d earned badges: %s", student_id, awarded)
    return awarded


async def update_streak(student_id: int) -> int:
    """Update current_streak_days from the gap between the two most recent
    sessions. Returns the new streak value. PROVISIONAL logic (RF-24)."""
    window_hours = settings.gamification_streak_hours_window
    async with database.async_session() as session:
        async with session.begin():
            student = await session.get(Student, student_id)
            if student is None:
                raise ValueError(f"Student {student_id} not found")

            sessions = (
                await session.execute(
                    select(Session)
                    .where(Session.student_id == student_id)
                    .order_by(Session.started_at.desc())
                )
            ).scalars().all()

            current = student.current_streak_days or 0
            if len(sessions) <= 1:
                new_streak = 1
            else:
                latest, previous = sessions[0].started_at, sessions[1].started_at
                if latest is None or previous is None:
                    new_streak = max(current, 1)
                else:
                    delta_hours = (latest - previous).total_seconds() / 3600
                    if delta_hours > window_hours:
                        new_streak = 1  # window exceeded -> streak broken
                    elif latest.date() != previous.date():
                        new_streak = current + 1  # a new active day within window
                    else:
                        new_streak = current or 1  # same day -> unchanged
            student.current_streak_days = new_streak
    return new_streak


async def get_gamification_state(student_id: int) -> dict:
    """Return {xp_points, current_streak_days, badges_earned}."""
    async with database.async_session() as session:
        student = await session.get(Student, student_id)
        if student is None:
            raise ValueError(f"Student {student_id} not found")
        return {
            "xp_points": student.xp_points or 0,
            "current_streak_days": student.current_streak_days or 0,
            "badges_earned": list(student.badges_earned or []),
        }
