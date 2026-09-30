"""Chat turn orchestration, shared by every transport (REST router, MCP server).

This is the single place where a tutoring turn is processed: prompt selection,
RAG context, LLM generation, history persistence and gamification. Transports
only translate their input/output and map the domain exceptions below.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.session import Session
from app.models.student import Student
from app.services import (
    gamification_service,
    llm_service,
    prompt_manager,
    rag_service,
)
from app.services.router_service import request_router

logger = logging.getLogger(__name__)


class StudentNotFound(Exception):
    """The requested student does not exist."""


class SessionNotFound(Exception):
    """The requested session does not exist or belongs to another student."""


@dataclass
class ChatTurnResult:
    response: str
    session_id: int
    prompt_type_used: str


async def process_chat_turn(
    db: AsyncSession,
    student_id: int,
    message: str,
    session_id: int | None = None,
) -> ChatTurnResult:
    student = await db.get(Student, student_id)
    if not student:
        raise StudentNotFound(student_id)

    if session_id:
        session = await db.get(Session, session_id)
        if not session or session.student_id != student.id:
            raise SessionNotFound(session_id)
    else:
        session = Session(student_id=student.id, message_history=[])
        db.add(session)
        await db.flush()

    history = session.message_history or []
    is_first = len(history) == 0

    prompt_type = prompt_manager.select_prompt_type(
        student_level=student.global_level,
        is_first_interaction=is_first,
    )

    student_context = {
        "student_name": student.name,
        "student_level": student.global_level,
        "module_name": "",
    }
    system_prompt = await prompt_manager.get_prompt(prompt_type, student_context)

    # Retrieve curricular context (RAG) only when the session is scoped to a
    # module — semantic search is module-scoped by design.
    if session.module_id is not None:
        chunks = await rag_service.search_context(
            message, module_id=session.module_id
        )
        if chunks:
            context_block = "\n\n---\nMaterial de referencia:\n" + "\n---\n".join(
                chunk.chunk_text for chunk in chunks
            )
            system_prompt += context_block

    # prompt_key is null on student turns: the pedagogical strategy applies to
    # the agent's reply, not to what the student wrote (RF-18 traceability).
    history.append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_key": None,
    })

    llm_messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
    ]

    # Choose the LLM provider (always "ollama" today; RF-23 will route complex
    # queries to Claude in a future phase) and generate the response.
    provider_name = await request_router.choose_provider(message, student_context)
    logger.info("Provider selected: %s", provider_name)
    provider = llm_service.get_provider(provider_name)
    reply = await provider.generate(
        llm_messages, system_prompt, temperature=settings.llm_temperature
    )

    # Record which pedagogical strategy produced this reply, so the teacher
    # panel can trace the agent's decisions turn by turn (RF-18).
    history.append({
        "role": "assistant",
        "content": reply,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_key": prompt_type,
    })
    session.message_history = history

    await db.commit()
    await db.refresh(session)

    # Gamification is best-effort and must never break the tutoring response:
    # the student's education comes before their game state (RF-16, RF-24).
    try:
        await gamification_service.award_xp(
            student.id, settings.gamification_xp_per_message, reason="chat_message"
        )
        # Streak first, so a streak milestone can be picked up by the badge
        # check in the same turn.
        await gamification_service.update_streak(student.id)
        await gamification_service.check_and_award_badges(student.id)
    except Exception:
        logger.exception(
            "Gamification update failed for student %s; returning chat response anyway",
            student.id,
        )

    return ChatTurnResult(
        response=reply,
        session_id=session.id,
        prompt_type_used=prompt_type,
    )
