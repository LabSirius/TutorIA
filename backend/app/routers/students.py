from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.student import (
    Student,
    StudentCreate,
    StudentProgress,
    StudentProgressRead,
    StudentRead,
    StudentUpdate,
)

router = APIRouter(prefix="/api/students", tags=["students"])


@router.post("", response_model=StudentRead, status_code=201)
async def create_student(
    payload: StudentCreate, db: AsyncSession = Depends(get_db)
):
    student = Student(**payload.model_dump())
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


@router.get("", response_model=list[StudentRead])
async def list_students(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student))
    return result.scalars().all()


@router.get("/{student_id}", response_model=StudentRead)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    student = await db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.patch("/{student_id}", response_model=StudentRead)
async def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: AsyncSession = Depends(get_db),
):
    student = await db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)

    await db.commit()
    await db.refresh(student)
    return student


@router.get("/{student_id}/progress", response_model=list[StudentProgressRead])
async def get_student_progress(
    student_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(StudentProgress).where(StudentProgress.student_id == student_id)
    )
    return result.scalars().all()
