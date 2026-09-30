"""OpenAI-compatible Chat Completions endpoint (Open edX AI Extensions, option B).

Lets the Open edX AI Extensions framework use TutorIA as its LLM provider. It is
only a transport: every turn is delegated to chat_service.process_chat_turn, the
same code /api/chat and the MCP tool use. TutorIA keeps its own session history,
so only the last user message of the request is used; the history the framework
sends is ignored.
"""
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.models.session import Session
from app.services.chat_service import (
    SessionNotFound,
    StudentNotFound,
    process_chat_turn,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["openai-compat"])


class ChatCompletionMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str
    # OpenAI allows either a plain string or a list of content parts.
    content: str | list[dict[str, Any]] | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatCompletionMessage]
    stream: bool = False
    # Accepted for compatibility; TutorIA applies its own generation settings.
    temperature: float | None = None
    user: str | None = None


def _message_text(message: ChatCompletionMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    if isinstance(message.content, list):
        return "".join(
            part.get("text", "") for part in message.content if part.get("type") == "text"
        )
    return ""


def _last_user_message(messages: list[ChatCompletionMessage]) -> str | None:
    for message in reversed(messages):
        if message.role == "user":
            text = _message_text(message).strip()
            return text or None
    return None


def _resolve_student_id(user: str | None) -> int:
    # TODO(fase-3b): map Open edX user ids to TutorIA student ids.
    if user is not None:
        try:
            return int(user.strip())
        except ValueError:
            pass
    return settings.openedx_default_student_id


async def _latest_session_id(db: AsyncSession, student_id: int) -> int | None:
    """Most recent session of the student, or None so a new one is created."""
    return await db.scalar(
        select(Session.id)
        .where(Session.student_id == student_id)
        .order_by(Session.started_at.desc(), Session.id.desc())
        .limit(1)
    )


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest, db: AsyncSession = Depends(get_db)
):
    message = _last_user_message(request.messages)
    if message is None:
        raise HTTPException(status_code=400, detail="No user message in messages")

    if request.stream:
        logger.warning(
            "stream=true requested on /v1/chat/completions; streaming is not "
            "supported yet, returning a non-streamed completion."
        )

    student_id = _resolve_student_id(request.user)
    session_id = await _latest_session_id(db, student_id)

    try:
        result = await process_chat_turn(db, student_id, message, session_id)
    except StudentNotFound:
        raise HTTPException(status_code=404, detail="Student not found")
    except SessionNotFound:
        # Unreachable in practice: the session was just looked up for this student.
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result.response},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
