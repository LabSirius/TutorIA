from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.session import Session
from app.models.student import Student
from app.services import llm_service, prompt_manager, rag_service

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
    student = await db.get(Student, request.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if request.session_id:
        session = await db.get(Session, request.session_id)
        if not session or session.student_id != student.id:
            raise HTTPException(status_code=404, detail="Session not found")
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
    system_prompt = prompt_manager.get_prompt(prompt_type, student_context)

    rag_context = rag_service.search_context(request.message, module_id=session.module_id)
    if rag_context:
        context_block = "\n\n---\nMaterial de referencia:\n" + "\n---\n".join(rag_context)
        system_prompt += context_block

    history.append({"role": "user", "content": request.message, "timestamp": datetime.now(timezone.utc).isoformat()})

    llm_messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
    ]

    reply = await llm_service.send_message(llm_messages, system_prompt)

    history.append({"role": "assistant", "content": reply, "timestamp": datetime.now(timezone.utc).isoformat()})
    session.message_history = history

    await db.commit()
    await db.refresh(session)

    return ChatResponse(
        response=reply,
        session_id=session.id,
        prompt_type_used=prompt_type,
    )
