import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

PROMPT_TYPES = [
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


@lru_cache(maxsize=None)
def _load_prompt(prompt_type: str) -> str:
    path = PROMPTS_DIR / f"{prompt_type}.txt"
    if not path.exists():
        logger.warning("Prompt file not found: %s", path)
        return ""
    return path.read_text(encoding="utf-8").strip()


def get_prompt(
    prompt_type: str,
    student_context: dict | None = None,
) -> str:
    template = _load_prompt(prompt_type)
    if not template:
        return _load_prompt("system_base")

    if student_context:
        for key, value in student_context.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))

    return template


def select_prompt_type(
    student_level: str = "beginner",
    consecutive_errors: int = 0,
    said_dont_know: bool = False,
    sessions_stuck: int = 0,
    expressed_frustration: bool = False,
    is_first_interaction: bool = False,
) -> str:
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
