from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.chat_service import (
    SessionNotFound,
    StudentNotFound,
    process_chat_turn,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    student_id: int
    message: str
    session_id: int | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: int
    prompt_type_used: str


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await process_chat_turn(
            db, request.student_id, request.message, request.session_id
        )
    except StudentNotFound:
        raise HTTPException(status_code=404, detail="Student not found")
    except SessionNotFound:
        raise HTTPException(status_code=404, detail="Session not found")

    return ChatResponse(
        response=result.response,
        session_id=result.session_id,
        prompt_type_used=result.prompt_type_used,
    )
