"""Seed data for the gamification badges (RF-16, RF-24).

Names/descriptions are Spanish because they are student-facing. The criteria in
`criteria_json` are PROVISIONAL placeholders to enable end-to-end testing; the
pedagogical team finalizes them later. Because the rules live in the database,
tuning them is a data change, not a code change.

Idempotent: only inserts badge keys that do not already exist.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import Badge

# (key, name, description, criteria_json)
BADGE_SEED: list[tuple[str, str, str, dict]] = [
    (
        "first_message",
        "Primer mensaje",
        "¡Iniciaste tu primera conversación con TutorIA!",
        {"type": "first_time_action", "action_key": "first_message"},
    ),
    (
        "streak_7_days",
        "Racha de 7 días",
        "Estudiaste 7 días seguidos. ¡Constancia!",
        {"type": "streak_days", "threshold": 7},
    ),
    (
        "first_module_completed",
        "Primer módulo completado",
        "Completaste tu primer módulo de aprendizaje.",
        {"type": "modules_completed", "threshold": 1},
    ),
    (
        "xp_100",
        "100 puntos de experiencia",
        "Alcanzaste 100 puntos de experiencia.",
        {"type": "xp_threshold", "threshold": 100},
    ),
    (
        "night_owl",
        "Búho nocturno",
        "Estudiaste en una sesión después de las 10 de la noche.",
        {"type": "first_time_action", "action_key": "late_night_session"},
    ),
]


async def seed_badges(session: AsyncSession) -> int:
    """Insert any missing badges. Returns the number inserted. Idempotent."""
    existing_keys = set(
        (await session.execute(select(Badge.key))).scalars().all()
    )

    inserted = 0
    for key, name, description, criteria in BADGE_SEED:
        if key in existing_keys:
            continue
        session.add(
            Badge(
                key=key,
                name=name,
                description=description,
                criteria_json=criteria,
            )
        )
        inserted += 1

    await session.flush()
    return inserted
