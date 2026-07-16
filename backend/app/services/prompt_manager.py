"""Loads and selects pedagogical prompts.

Prompt CONTENT now lives in the database (prompt_templates table), editable and
versioned by teachers (RF-21). This module loads active templates into an
in-memory cache and applies the Marco Pedagógico V2 adaptability rules to decide
which prompt to use. Only the source of the content changed; the rules are the
same as when prompts lived in .txt files.
"""
import logging

from sqlalchemy import select

from app.db import database
from app.models.prompt_template import PromptTemplate

logger = logging.getLogger(__name__)

# The ten pedagogical prompt keys TutorIA relies on (Marco V2).
PROMPT_KEYS = [
    "system_base",
    "diagnostic",
    "basic_explanation",
    "advanced_explanation",
    "comprehension_check",
    "socratic",
    "cognitive_modeling",
    "error_feedback",
    "risk_alert",
    "metacognitive_closure",
]


class PromptTemplateNotFoundError(RuntimeError):
    """Raised when a requested prompt key has no active template in the database."""


# In-memory cache of active prompt content, keyed by `key`.
_cache: dict[str, str] = {}
_warmed: bool = False


async def _load_active_templates() -> dict[str, str]:
    async with database.async_session() as session:
        rows = (
            await session.execute(
                select(PromptTemplate).where(PromptTemplate.is_active.is_(True))
            )
        ).scalars().all()
    return {template.key: template.content for template in rows}


async def warm_cache() -> int:
    """Load all active templates into the in-memory cache. Returns the count.
    Called on startup and after cache invalidation."""
    global _warmed
    templates = await _load_active_templates()
    _cache.clear()
    _cache.update(templates)
    _warmed = True
    logger.info("Warmed %d active prompt template(s) into cache.", len(_cache))
    return len(_cache)


def invalidate_cache() -> None:
    """Clear the cache so the next get_prompt reloads from the database. The
    future admin endpoint calls this after a teacher edits a template."""
    global _warmed
    _cache.clear()
    _warmed = False


async def get_prompt(prompt_key: str, student_context: dict | None = None) -> str:
    """Return the active prompt content for `prompt_key`, substituting any
    {{var}} placeholders from student_context.

    Fails loudly with PromptTemplateNotFoundError if the key has no active
    template — it never returns an empty-string fallback, so a missing/misnamed
    prompt surfaces immediately instead of silently degrading the tutoring.
    """
    if not _warmed:
        await warm_cache()
    if prompt_key not in _cache:
        raise PromptTemplateNotFoundError(
            f"No active prompt template for key '{prompt_key}'. "
            f"Seed the prompts with:  python -m app.db.seed prompts"
        )
    content = _cache[prompt_key]
    if student_context:
        for key, value in student_context.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
    return content


def select_prompt_type(
    student_level: str = "beginner",
    consecutive_errors: int = 0,
    said_dont_know: bool = False,
    sessions_stuck: int = 0,
    expressed_frustration: bool = False,
    is_first_interaction: bool = False,
) -> str:
    # Adaptability rules from Marco Pedagógico V2 — unchanged by the move to the
    # database (only the source of the prompt content changed):
    #   new student            -> diagnostic
    #   frustration detected   -> risk_alert
    #   student says "I don't know" -> basic_explanation
    #   same error 2+ times    -> socratic
    #   3+ sessions stuck       -> cognitive_modeling (teacher-alert flow)
    #   advanced student        -> advanced_explanation
    if is_first_interaction:
        return "diagnostic"
    if expressed_frustration:
        return "risk_alert"
    if said_dont_know:
        return "basic_explanation"
    if consecutive_errors >= 2:
        return "socratic"
    if sessions_stuck >= 3:
        return "cognitive_modeling"
    if student_level == "advanced":
        return "advanced_explanation"
    return "basic_explanation"
