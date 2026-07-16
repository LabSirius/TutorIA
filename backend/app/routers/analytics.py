from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.analytics import (
    ConversationSummary,
    ConversationsPage,
    CourseSummary,
    RiskAlert,
    SessionMetadata,
    StudentDetail,
    TranscriptMessage,
    TranscriptResponse,
)
from app.models.evaluation import Evaluation
from app.models.module import Module, Subject
from app.models.session import Session
from app.models.student import Student, StudentProgress
from app.models.teacher import TeacherCourse

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Teacher authorization (RF-18)
#
# A teacher may only see a student's conversations if they are assigned
# (teacher_courses) to a subject that student is actually working in. The
# student's subjects are derived from their sessions' and progress' modules,
# because there is no direct student<->subject enrolment table yet (it will
# arrive with the Open edX gateway).
# ---------------------------------------------------------------------------

async def _teacher_subject_ids(db: AsyncSession, teacher_id: int) -> set[int]:
    rows = (
        await db.execute(
            select(TeacherCourse.subject_id).where(
                TeacherCourse.teacher_id == teacher_id
            )
        )
    ).scalars().all()
    return set(rows)


async def _student_subject_ids(db: AsyncSession, student_id: int) -> set[int]:
    via_sessions = (
        select(Module.subject_id)
        .join(Session, Session.module_id == Module.id)
        .where(Session.student_id == student_id)
    )
    via_progress = (
        select(Module.subject_id)
        .join(StudentProgress, StudentProgress.module_id == Module.id)
        .where(StudentProgress.student_id == student_id)
    )
    rows = (await db.execute(via_sessions.union(via_progress))).scalars().all()
    return {row for row in rows if row is not None}


async def _ensure_teacher_can_access_student(
    db: AsyncSession, teacher_id: int, student_id: int
) -> None:
    teacher_subjects = await _teacher_subject_ids(db, teacher_id)
    if not teacher_subjects:
        raise HTTPException(
            status_code=403, detail="Teacher is not assigned to any course"
        )
    student_subjects = await _student_subject_ids(db, student_id)
    if not (teacher_subjects & student_subjects):
        raise HTTPException(
            status_code=403, detail="Teacher is not assigned to this student's course"
        )


async def verify_teacher_for_student(
    student_id: int,
    x_teacher_id: int = Header(..., alias="X-Teacher-Id"),
    db: AsyncSession = Depends(get_db),
) -> int:
    # TODO: replace with proper JWT auth from Open edX in a later phase.
    await _ensure_teacher_can_access_student(db, x_teacher_id, student_id)
    return x_teacher_id


async def verify_teacher_for_session(
    session_id: int,
    x_teacher_id: int = Header(..., alias="X-Teacher-Id"),
    db: AsyncSession = Depends(get_db),
) -> Session:
    # TODO: replace with proper JWT auth from Open edX in a later phase.
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await _ensure_teacher_can_access_student(db, x_teacher_id, session.student_id)
    return session


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


# ---------------------------------------------------------------------------
# Conversation traceability (RF-18)
# ---------------------------------------------------------------------------

@router.get(
    "/student/{student_id}/conversations", response_model=ConversationsPage
)
async def student_conversations(
    student_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _teacher_id: int = Depends(verify_teacher_for_student),
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of a student's tutoring sessions with metadata."""
    total = (
        await db.execute(
            select(func.count())
            .select_from(Session)
            .where(Session.student_id == student_id)
        )
    ).scalar() or 0

    rows = (
        await db.execute(
            select(Session, Module, Subject)
            .outerjoin(Module, Session.module_id == Module.id)
            .outerjoin(Subject, Module.subject_id == Subject.id)
            .where(Session.student_id == student_id)
            .order_by(Session.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = []
    for session, module, subject in rows:
        duration = None
        if session.ended_at and session.started_at:
            duration = round(
                (session.ended_at - session.started_at).total_seconds() / 60, 2
            )
        items.append(
            ConversationSummary(
                session_id=session.id,
                module_id=session.module_id,
                subject_id=subject.id if subject else None,
                module_name=module.name if module else None,
                subject_name=subject.name if subject else None,
                started_at=session.started_at,
                ended_at=session.ended_at,
                message_count=len(session.message_history or []),
                duration_minutes=duration,
            )
        )

    return ConversationsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/session/{session_id}/transcript", response_model=TranscriptResponse)
async def session_transcript(
    session: Session = Depends(verify_teacher_for_session),
    db: AsyncSession = Depends(get_db),
):
    """Full message history of a session, including the pedagogical strategy
    (prompt_key) used at each agent turn."""
    subject_id = None
    if session.module_id is not None:
        module = await db.get(Module, session.module_id)
        subject_id = module.subject_id if module else None

    messages = [
        TranscriptMessage(
            role=entry.get("role", "unknown"),
            content=entry.get("content", ""),
            timestamp=entry.get("timestamp"),
            prompt_key=entry.get("prompt_key"),
        )
        for entry in (session.message_history or [])
    ]

    return TranscriptResponse(
        session_metadata=SessionMetadata(
            session_id=session.id,
            student_id=session.student_id,
            module_id=session.module_id,
            subject_id=subject_id,
            started_at=session.started_at,
            ended_at=session.ended_at,
        ),
        messages=messages,
    )
