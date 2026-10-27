"""OpenAI-compatible Chat Completions endpoint (Open edX AI Extensions, option B).

Lets the Open edX AI Extensions framework use TutorIA as its LLM provider. It is
only a transport: every turn is delegated to chat_service.stream_chat_turn (the
same pedagogy as process_chat_turn, used by /api/chat and the MCP tool), which
yields LLM tokens as they are generated. TutorIA keeps its own session history,
so only the last user message of the request is used; the history the framework
sends is ignored. The session continues while active (resolve_active_session).

Each turn runs as the student's registered generation (generation_registry):
Open edX does not forward browser disconnects, so a new request of the same
student cancels the previous generation instead of letting it run on in Ollama.
"""
import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import anyio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from app.config import settings
from app.db import database
from app.services.chat_service import (
    SessionNotFound,
    StudentNotFound,
    resolve_active_session,
    stream_chat_turn,
)
from app.services.generation_registry import generations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["openai-compat"])

# Returned when the framework calls with no user message (e.g. on chat open).
WELCOME_MESSAGE = "¡Hola! Soy TutorIA. ¿En qué tema quieres que trabajemos hoy?"

# Seconds between SSE keepalive comments while a streamed reply is generated.
KEEPALIVE_INTERVAL_SECONDS = 15

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


# Last item a generation puts on its queue.
_END = object()


async def _run_generation(queue: asyncio.Queue, student_id: int, message: str) -> None:
    """Run one turn, putting its text deltas on `queue`, then an error if any, then _END.

    Runs as the student's registered task, so a newer request (or this request's
    client disconnecting) cancels it: stream_chat_turn then closes the LLM stream
    and persists the partial reply as interrupted.
    """
    try:
        # The task owns its db session; it can outlive the request that started it.
        async with database.async_session() as db:
            session_id = await resolve_active_session(db, student_id)
            async for token in stream_chat_turn(db, student_id, message, session_id):
                queue.put_nowait(token)
    except Exception as exc:
        queue.put_nowait(exc)
    finally:
        queue.put_nowait(_END)


async def _start_generation(request: ChatCompletionRequest, message: str) -> tuple[asyncio.Task, asyncio.Queue]:
    student_id = _resolve_student_id(request.user)
    queue: asyncio.Queue = asyncio.Queue()
    task = await generations.start(
        student_id, lambda: _run_generation(queue, student_id, message)
    )
    return task, queue


async def _stop_generation(task: asyncio.Task | None) -> None:
    # Shielded: under anyio cancellation (client disconnect) every await would
    # be cancelled again before the interrupted turn is persisted.
    with anyio.CancelScope(shield=True):
        if task is not None and not task.done():
            task.cancel()
            await asyncio.wait({task})


async def _stream_completion(
    request: ChatCompletionRequest, message: str | None
) -> AsyncIterator[str]:
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    model = request.model

    # Sent before any slow work so the client sees the connection is alive.
    yield _chunk(completion_id, created, model, {"role": "assistant"})

    if message is None:
        for piece in _split_for_streaming(WELCOME_MESSAGE):
            yield _chunk(completion_id, created, model, {"content": piece})
    else:
        task = None
        try:
            task, queue = await _start_generation(request, message)
            has_content = False
            while True:
                if has_content:
                    item = await queue.get()
                else:
                    # SSE comments keep proxies and clients from timing out the
                    # connection until the first token (prompt processing on CPU is slow).
                    try:
                        item = await asyncio.wait_for(queue.get(), KEEPALIVE_INTERVAL_SECONDS)
                    except TimeoutError:
                        yield ": keepalive\n\n"
                        continue
                if item is _END:
                    # Also reached when a newer request of the student cancelled this one.
                    break
                if isinstance(item, Exception):
                    raise item
                has_content = True
                yield _chunk(completion_id, created, model, {"content": item})
        except Exception:
            logger.exception("Error generating a streamed chat completion")
            yield _chunk(completion_id, created, model, {"content": STREAM_ERROR_MESSAGE})
        finally:
            # Also runs when the client disconnects: cancelling the generation
            # stops Ollama and persists the partial reply as interrupted.
            await _stop_generation(task)

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
async def chat_completions(request: ChatCompletionRequest):
    # The framework may open the chat with only system messages. Answer with a
    # static welcome without touching the LLM, the student or any session.
    has_user_message = any(m.role == "user" for m in request.messages)

    message = None
    if has_user_message:
        message = _last_user_message(request.messages)
        if message is None:
            raise HTTPException(status_code=400, detail="No user message in messages")

    if request.stream:
        return StreamingResponse(
            _stream_completion(request, message),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if message is None:
        return _completion(request.model, WELCOME_MESSAGE)

    # Same registered generation as streaming, so a newer request of the student
    # can cancel this one too; its reply is then the partial text generated so far.
    task = None
    try:
        task, queue = await _start_generation(request, message)
        await asyncio.wait({task})
    finally:
        await _stop_generation(task)

    parts = []
    while (item := queue.get_nowait()) is not _END:
        if isinstance(item, StudentNotFound):
            raise HTTPException(status_code=404, detail="Student not found")
        if isinstance(item, SessionNotFound):
            # Unreachable in practice: the session was just resolved for this student.
            raise HTTPException(status_code=404, detail="Session not found")
        if isinstance(item, Exception):
            raise item
        parts.append(item)

    return _completion(request.model, "".join(parts))
