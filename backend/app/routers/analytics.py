from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.analytics import CourseSummary, RiskAlert, StudentDetail
from app.models.evaluation import Evaluation
from app.models.module import Module
from app.models.session import Session
from app.models.student import Student, StudentProgress

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/course/{subject_id}/summary", response_model=CourseSummary)
async def course_summary(
    subject_id: int, db: AsyncSession = Depends(get_db)
):
    module_ids_q = select(Module.id).where(Module.subject_id == subject_id)

    active_q = (
        select(func.count(func.distinct(Session.student_id)))
        .where(Session.module_id.in_(module_ids_q))
    )
    active_result = await db.execute(active_q)
    active_students = active_result.scalar() or 0

    progress_q = (
        select(func.avg(StudentProgress.attempts))
        .where(StudentProgress.module_id.in_(module_ids_q))
    )
    progress_result = await db.execute(progress_q)
    average_progress = float(progress_result.scalar() or 0)

    eval_q = (
        select(func.avg(Evaluation.score))
        .where(Evaluation.module_id.in_(module_ids_q))
        .where(Evaluation.score.is_not(None))
    )
    eval_result = await db.execute(eval_q)
    approval_rate = float(eval_result.scalar() or 0)

    return CourseSummary(
        active_students=active_students,
        average_progress=average_progress,
        approval_rate=approval_rate,
    )


@router.get("/student/{student_id}/detail", response_model=StudentDetail)
async def student_detail(
    student_id: int, db: AsyncSession = Depends(get_db)
):
    student = await db.get(Student, student_id)
    name = student.name if student else "Unknown"

    completed_q = (
        select(func.count())
        .select_from(StudentProgress)
        .where(StudentProgress.student_id == student_id)
        .where(StudentProgress.module_level == "completed")
    )
    completed_result = await db.execute(completed_q)
    modules_completed = completed_result.scalar() or 0

    sessions_q = (
        select(func.count())
        .select_from(Session)
        .where(Session.student_id == student_id)
    )
    sessions_result = await db.execute(sessions_q)
    total_sessions = sessions_result.scalar() or 0

    score_q = (
        select(func.avg(Evaluation.score))
        .where(Evaluation.student_id == student_id)
        .where(Evaluation.score.is_not(None))
    )
    score_result = await db.execute(score_q)
    average_score = score_result.scalar()

    return StudentDetail(
        student_id=student_id,
        name=name,
        modules_completed=modules_completed,
        total_sessions=total_sessions,
        total_time_minutes=0.0,
        average_score=float(average_score) if average_score else None,
    )


@router.get("/course/{subject_id}/alerts", response_model=list[RiskAlert])
async def course_alerts(
    subject_id: int, db: AsyncSession = Depends(get_db)
):
    # TODO: implement risk detection based on Marco Pedagógico V2 rules:
    # - inactivity > 5 days
    # - 3+ sessions stuck on same concept
    # - expressions of frustration in message history
    return []
