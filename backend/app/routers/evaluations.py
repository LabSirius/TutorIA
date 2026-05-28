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

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


@router.post("", response_model=EvaluationRead, status_code=201)
async def create_evaluation(
    payload: EvaluationCreate, db: AsyncSession = Depends(get_db)
):
    evaluation = Evaluation(**payload.model_dump())
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


@router.get("", response_model=list[EvaluationRead])
async def list_evaluations(
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


@router.get("/{evaluation_id}", response_model=EvaluationRead)
async def get_evaluation(
    evaluation_id: int, db: AsyncSession = Depends(get_db)
):
    evaluation = await db.get(Evaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


@router.post("/{evaluation_id}/submit", response_model=EvaluationRead)
async def submit_evaluation(
    evaluation_id: int,
    payload: EvaluationSubmit,
    db: AsyncSession = Depends(get_db),
):
    evaluation = await db.get(Evaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    evaluation.answers = payload.answers
    # TODO: scoring logic — will use LLM to grade open-ended answers
    await db.commit()
    await db.refresh(evaluation)
    return evaluation
