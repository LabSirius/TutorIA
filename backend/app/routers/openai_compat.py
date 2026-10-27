"""OpenAI-compatible Chat Completions endpoint (Open edX AI Extensions, option B).

Lets the Open edX AI Extensions framework use TutorIA as its LLM provider. It is
only a transport: every turn is delegated to chat_service.process_chat_turn, the
same code /api/chat and the MCP tool use. TutorIA keeps its own session history,
so only the last user message of the request is used; the history the framework
sends is ignored.
"""
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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

# Returned when the framework calls with no user message (e.g. on chat open).
WELCOME_MESSAGE = "¡Hola! Soy TutorIA. ¿En qué tema quieres que trabajemos hoy?"

# Sent as the last content delta when a streamed reply fails after it started.
STREAM_ERROR_MESSAGE = (
    "Lo siento, ocurrió un error al generar la respuesta. Intenta de nuevo en un momento."
)


class ChatCompletionMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str
    # OpenAI allows either a plain string or a list of content parts.
    content: str | list[dict[str, Any]] | None = None


class StreamOptions(BaseModel):
    model_config = ConfigDict(extra="ignore")

    include_usage: bool = False


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatCompletionMessage]
    stream: bool = False
    stream_options: StreamOptions | None = None
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


def _completion(model: str, content: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _chunk(
    completion_id: str,
    created: int,
    model: str,
    delta: dict[str, Any],
    finish_reason: str | None = None,
) -> str:
    chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def _split_for_streaming(text: str) -> list[str]:
    """Split text into word pieces (with their trailing whitespace) that concatenate back to it."""
    return re.findall(r"\S+\s*|\s+", text)


async def _tutor_reply(db: AsyncSession, request: ChatCompletionRequest, message: str) -> str:
    student_id = _resolve_student_id(request.user)
    session_id = await _latest_session_id(db, student_id)
    result = await process_chat_turn(db, student_id, message, session_id)
    return result.response


async def _stream_completion(
    db: AsyncSession, request: ChatCompletionRequest, message: str | None
) -> AsyncIterator[str]:
    # Pseudo-streaming: the full reply is generated first, then emitted in pieces.
    # TODO(fase-3b): stream tokens from the LLM as they are generated.
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    model = request.model

    # Sent before any slow work so the client sees the connection is alive.
    yield _chunk(completion_id, created, model, {"role": "assistant"})

    if message is None:
        reply = WELCOME_MESSAGE
    else:
        try:
            reply = await _tutor_reply(db, request, message)
        except Exception:
            logger.exception("Error generating a streamed chat completion")
            reply = STREAM_ERROR_MESSAGE

    for piece in _split_for_streaming(reply):
        yield _chunk(completion_id, created, model, {"content": piece})

    yield _chunk(completion_id, created, model, {}, finish_reason="stop")

    if request.stream_options and request.stream_options.include_usage:
        usage_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
        yield f"data: {json.dumps(usage_chunk)}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest, db: AsyncSession = Depends(get_db)
):
    # The framework may open the chat with only system messages. Answer with a
    # static welcome without touching the LLM, the student or any session.
    has_user_message = any(m.role == "user" for m in request.messages)

    message = None
    if has_user_message:
        message = _last_user_message(request.messages)
        if message is None:
            raise HTTPException(status_code=400, detail="No user message in messages")

    if request.stream:
        # The db session stays open while streaming: FastAPI (>=0.118) closes
        # yield dependencies only after the response has been sent.
        return StreamingResponse(
            _stream_completion(db, request, message),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if message is None:
        return _completion(request.model, WELCOME_MESSAGE)

    try:
        reply = await _tutor_reply(db, request, message)
    except StudentNotFound:
        raise HTTPException(status_code=404, detail="Student not found")
    except SessionNotFound:
        # Unreachable in practice: the session was just looked up for this student.
        raise HTTPException(status_code=404, detail="Session not found")

    return _completion(request.model, reply)
