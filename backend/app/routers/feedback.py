"""Continuous formative feedback + gamification endpoints (RF-15, RF-16, RF-24).

Exposed under /api/feedback. The underlying table is still named `evaluations`
for historical reasons (see models/evaluation.py); "feedback event" is the
semantic meaning — formative, not summative.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.evaluation import (
    Evaluation,
    EvaluationCreate,
    EvaluationRead,
    EvaluationSubmit,
)
from app.models.gamification import (
    GamificationState,
    XpAwardRequest,
    XpAwardResponse,
)
from app.services import gamification_service

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


# ---------------------------------------------------------------------------
# Feedback events (formerly "evaluations" — same table, renamed surface)
# ---------------------------------------------------------------------------

@router.post("", response_model=EvaluationRead, status_code=201)
async def create_feedback(
    payload: EvaluationCreate, db: AsyncSession = Depends(get_db)
):
    feedback_event = Evaluation(**payload.model_dump())
    db.add(feedback_event)
    await db.commit()
    await db.refresh(feedback_event)
    return feedback_event


@router.get("", response_model=list[EvaluationRead])
async def list_feedback(
    student_id: int | None = None,
    module_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Evaluation)
    if student_id is not None:
        query = query.where(Evaluation.student_id == student_id)
    if module_id is not None:
        query = query.where(Evaluation.module_id == module_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{feedback_id}", response_model=EvaluationRead)
async def get_feedback(feedback_id: int, db: AsyncSession = Depends(get_db)):
    feedback_event = await db.get(Evaluation, feedback_id)
    if not feedback_event:
        raise HTTPException(status_code=404, detail="Feedback event not found")
    return feedback_event


@router.post("/{feedback_id}/submit", response_model=EvaluationRead)
async def submit_feedback(
    feedback_id: int,
    payload: EvaluationSubmit,
    db: AsyncSession = Depends(get_db),
):
    feedback_event = await db.get(Evaluation, feedback_id)
    if not feedback_event:
        raise HTTPException(status_code=404, detail="Feedback event not found")

    feedback_event.answers = payload.answers
    # TODO: scoring logic — will use the LLM to grade open-ended answers.
    await db.commit()
    await db.refresh(feedback_event)
    return feedback_event


# ---------------------------------------------------------------------------
# Gamification
# ---------------------------------------------------------------------------

@router.post("/xp", response_model=XpAwardResponse)
async def award_xp(payload: XpAwardRequest):
    try:
        new_total = await gamification_service.award_xp(
            payload.student_id, payload.amount, payload.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return XpAwardResponse(student_id=payload.student_id, xp_points=new_total)


@router.get("/gamification/{student_id}", response_model=GamificationState)
async def get_gamification(student_id: int):
    try:
        state = await gamification_service.get_gamification_state(student_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GamificationState(student_id=student_id, **state)
