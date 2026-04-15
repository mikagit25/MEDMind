"""
Courses router — teacher creates/manages courses; students join and follow progress.

Endpoints
─────────
Teacher:
  POST   /courses                          create course
  GET    /courses/my                       list own courses
  GET    /courses/{id}                     course detail + modules + enrollments count
  PATCH  /courses/{id}                     update title/description/dates
  DELETE /courses/{id}                     soft-delete (is_active=false)

  POST   /courses/{id}/modules             add module to course
  DELETE /courses/{id}/modules/{module_id} remove module
  PATCH  /courses/{id}/modules/reorder     reorder modules

  POST   /courses/{id}/assignments         create assignment (module + due_date)
  DELETE /courses/{id}/assignments/{aid}   remove assignment

  GET    /courses/{id}/students            list enrolled students + their progress
  DELETE /courses/{id}/students/{uid}      remove student

Student:
  POST   /courses/join                     join by invite_code
  GET    /courses/enrolled                 list enrolled courses
  GET    /courses/{id}/my-progress         own progress per module in course
  DELETE /courses/{id}/leave               leave course
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import (
    Course, CourseModule, CourseEnrollment, CourseAssignment,
    Module, User, UserProgress,
)

router = APIRouter(prefix="/courses", tags=["courses"])


# ── helpers ────────────────────────────────────────────────────────────────

def _require_teacher(user: User):
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Teacher role required")


async def _get_course_or_404(course_id: UUID, db: AsyncSession) -> Course:
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.course_modules).selectinload(CourseModule.module),
            selectinload(Course.assignments),
        )
        .where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# ── schemas ────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class AssignmentCreate(BaseModel):
    module_id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    max_score: int = 100


class ReorderBody(BaseModel):
    module_ids: List[UUID]  # ordered list


class ModuleOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    lesson_count: int = 0
    module_order: int


class AssignmentOut(BaseModel):
    id: UUID
    module_id: UUID
    title: Optional[str]
    description: Optional[str]
    due_date: Optional[str]
    max_score: int


class CourseOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    invite_code: str
    is_active: bool
    starts_at: Optional[str]
    ends_at: Optional[str]
    created_at: str
    module_count: int
    student_count: int
    modules: List[ModuleOut] = []
    assignments: List[AssignmentOut] = []

    @classmethod
    def from_orm_obj(cls, c: Course, student_count: int = 0) -> "CourseOut":
        modules = sorted(c.course_modules, key=lambda cm: cm.module_order)
        return cls(
            id=c.id,
            title=c.title,
            description=c.description,
            invite_code=c.invite_code,
            is_active=c.is_active,
            starts_at=c.starts_at.isoformat() if c.starts_at else None,
            ends_at=c.ends_at.isoformat() if c.ends_at else None,
            created_at=c.created_at.isoformat(),
            module_count=len(c.course_modules),
            student_count=student_count,
            modules=[
                ModuleOut(
                    id=cm.module.id,
                    title=cm.module.title,
                    description=cm.module.description,
                    module_order=cm.module_order,
                )
                for cm in modules
            ],
            assignments=[
                AssignmentOut(
                    id=a.id,
                    module_id=a.module_id,
                    title=a.title,
                    description=a.description,
                    due_date=a.due_date.isoformat() if a.due_date else None,
                    max_score=a.max_score,
                )
                for a in c.assignments
            ],
        )


class StudentProgressOut(BaseModel):
    student_id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    enrolled_at: str
    status: str
    modules_progress: List[dict]  # {module_id, title, completion_percent, lessons_done, last_activity}


# ── TEACHER endpoints ──────────────────────────────────────────────────────

@router.post("", response_model=CourseOut, status_code=201)
async def create_course(
    body: CourseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    course = Course(
        teacher_id=user.id,
        title=body.title,
        description=body.description,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    # reload with relationships
    course = await _get_course_or_404(course.id, db)
    return CourseOut.from_orm_obj(course, 0)


@router.post("/join", status_code=201)
async def join_course(
    invite_code: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Student joins a course by invite code."""
    result = await db.execute(
        select(Course).where(Course.invite_code == invite_code.upper(), Course.is_active == True)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Invalid or expired invite code")

    # Idempotent
    existing = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.student_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"ok": True, "course_id": str(course.id), "already_enrolled": True}

    enr = CourseEnrollment(course_id=course.id, student_id=user.id)
    db.add(enr)
    await db.commit()
    return {"ok": True, "course_id": str(course.id), "already_enrolled": False, "title": course.title}


@router.get("/enrolled", response_model=List[CourseOut])
async def get_enrolled_courses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all courses the student is enrolled in."""
    enr_result = await db.execute(
        select(CourseEnrollment.course_id)
        .where(CourseEnrollment.student_id == user.id, CourseEnrollment.status == "active")
    )
    course_ids = [row[0] for row in enr_result.fetchall()]
    if not course_ids:
        return []

    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.course_modules).selectinload(CourseModule.module),
            selectinload(Course.assignments),
        )
        .where(Course.id.in_(course_ids), Course.is_active == True)
        .order_by(Course.created_at.desc())
    )
    courses = result.scalars().all()
    return [CourseOut.from_orm_obj(c, 0) for c in courses]


@router.get("/my", response_model=List[CourseOut])
async def list_my_courses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.course_modules).selectinload(CourseModule.module),
            selectinload(Course.assignments),
            selectinload(Course.enrollments),
        )
        .where(Course.teacher_id == user.id)
        .order_by(Course.created_at.desc())
    )
    courses = result.scalars().all()
    return [CourseOut.from_orm_obj(c, len(c.enrollments)) for c in courses]


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    course = await _get_course_or_404(course_id, db)
    # Only teacher or enrolled student can view
    if str(course.teacher_id) != str(user.id) and user.role not in ("admin",):
        # check enrollment
        enr = await db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.student_id == user.id,
            )
        )
        if not enr.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not enrolled in this course")
    count_result = await db.execute(
        select(func.count()).select_from(CourseEnrollment)
        .where(CourseEnrollment.course_id == course_id)
    )
    return CourseOut.from_orm_obj(course, count_result.scalar() or 0)


@router.patch("/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: UUID,
    body: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    course = await _get_course_or_404(course_id, db)
    if str(course.teacher_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Not your course")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(course, field, value)
    await db.commit()
    course = await _get_course_or_404(course_id, db)
    count_result = await db.execute(
        select(func.count()).select_from(CourseEnrollment)
        .where(CourseEnrollment.course_id == course_id)
    )
    return CourseOut.from_orm_obj(course, count_result.scalar() or 0)


@router.delete("/{course_id}", status_code=204)
async def delete_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    course = await _get_course_or_404(course_id, db)
    if str(course.teacher_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Not your course")
    course.is_active = False
    await db.commit()


# ── Modules management ─────────────────────────────────────────────────────

@router.post("/{course_id}/modules", status_code=201)
async def add_module_to_course(
    course_id: UUID,
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    course = await _get_course_or_404(course_id, db)
    if str(course.teacher_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Not your course")
    # verify module exists
    mod = await db.get(Module, module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")
    # check duplicate
    existing = await db.execute(
        select(CourseModule).where(
            CourseModule.course_id == course_id,
            CourseModule.module_id == module_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Module already in course")
    order = len(course.course_modules)
    cm = CourseModule(course_id=course_id, module_id=module_id, module_order=order)
    db.add(cm)
    await db.commit()
    return {"ok": True}


@router.delete("/{course_id}/modules/{module_id}", status_code=204)
async def remove_module_from_course(
    course_id: UUID,
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    result = await db.execute(
        select(CourseModule).where(
            CourseModule.course_id == course_id,
            CourseModule.module_id == module_id,
        )
    )
    cm = result.scalar_one_or_none()
    if not cm:
        raise HTTPException(status_code=404, detail="Module not in course")
    await db.delete(cm)
    await db.commit()


@router.patch("/{course_id}/modules/reorder", status_code=200)
async def reorder_modules(
    course_id: UUID,
    body: ReorderBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    for idx, mod_id in enumerate(body.module_ids):
        result = await db.execute(
            select(CourseModule).where(
                CourseModule.course_id == course_id,
                CourseModule.module_id == mod_id,
            )
        )
        cm = result.scalar_one_or_none()
        if cm:
            cm.module_order = idx
    await db.commit()
    return {"ok": True}


# ── Assignments ────────────────────────────────────────────────────────────

@router.post("/{course_id}/assignments", response_model=AssignmentOut, status_code=201)
async def create_assignment(
    course_id: UUID,
    body: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    course = await _get_course_or_404(course_id, db)
    if str(course.teacher_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Not your course")
    assignment = CourseAssignment(
        course_id=course_id,
        module_id=body.module_id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        max_score=body.max_score,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return AssignmentOut(
        id=assignment.id,
        module_id=assignment.module_id,
        title=assignment.title,
        description=assignment.description,
        due_date=assignment.due_date.isoformat() if assignment.due_date else None,
        max_score=assignment.max_score,
    )


@router.delete("/{course_id}/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    course_id: UUID,
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    result = await db.execute(
        select(CourseAssignment).where(
            CourseAssignment.id == assignment_id,
            CourseAssignment.course_id == course_id,
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.delete(assignment)
    await db.commit()


# ── Student monitoring ─────────────────────────────────────────────────────

@router.get("/{course_id}/students", response_model=List[StudentProgressOut])
async def get_students_progress(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    course = await _get_course_or_404(course_id, db)
    if str(course.teacher_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Not your course")

    # Get all enrollments with student data
    enr_result = await db.execute(
        select(CourseEnrollment)
        .options(selectinload(CourseEnrollment.student))
        .where(CourseEnrollment.course_id == course_id)
        .order_by(CourseEnrollment.enrolled_at)
    )
    enrollments = enr_result.scalars().all()

    module_ids = [cm.module_id for cm in course.course_modules]
    student_ids = [enr.student_id for enr in enrollments]
    sorted_cms = sorted(course.course_modules, key=lambda x: x.module_order)

    # Batch-load all UserProgress rows for these students × modules in one query
    prog_map: dict[tuple, UserProgress] = {}
    if student_ids and module_ids:
        prog_rows = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id.in_(student_ids),
                UserProgress.module_id.in_(module_ids),
            )
        )
        for p in prog_rows.scalars().all():
            prog_map[(p.user_id, p.module_id)] = p

    out = []
    for enr in enrollments:
        student = enr.student
        modules_progress = []
        for cm in sorted_cms:
            prog = prog_map.get((student.id, cm.module_id))
            modules_progress.append({
                "module_id": str(cm.module_id),
                "title": cm.module.title,
                "completion_percent": float(prog.completion_percent) if prog else 0.0,
                "lessons_done": len(prog.lessons_completed) if prog and prog.lessons_completed else 0,
                "last_activity": prog.last_activity_at.isoformat() if prog and prog.last_activity_at else None,
            })
        out.append(StudentProgressOut(
            student_id=student.id,
            email=student.email,
            first_name=student.first_name,
            last_name=student.last_name,
            enrolled_at=enr.enrolled_at.isoformat(),
            status=enr.status,
            modules_progress=modules_progress,
        ))
    return out


@router.delete("/{course_id}/students/{student_id}", status_code=204)
async def remove_student(
    course_id: UUID,
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    result = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
    )
    enr = result.scalar_one_or_none()
    if not enr:
        raise HTTPException(status_code=404, detail="Student not enrolled")
    await db.delete(enr)
    await db.commit()


# ── STUDENT progress & leave ───────────────────────────────────────────────

@router.get("/{course_id}/my-progress")
async def get_my_progress(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Student views their own progress in a course."""
    # verify enrollment
    enr = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == user.id,
        )
    )
    if not enr.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    course = await _get_course_or_404(course_id, db)
    module_ids = [cm.module_id for cm in course.course_modules]

    # Batch-load progress for this user across all course modules
    prog_map: dict = {}
    if module_ids:
        prog_rows = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.module_id.in_(module_ids),
            )
        )
        prog_map = {p.module_id: p for p in prog_rows.scalars().all()}

    progress = []
    for cm in sorted(course.course_modules, key=lambda x: x.module_order):
        prog = prog_map.get(cm.module_id)
        progress.append({
            "module_id": str(cm.module_id),
            "title": cm.module.title,
            "completion_percent": float(prog.completion_percent) if prog else 0.0,
            "lessons_done": len(prog.lessons_completed) if prog and prog.lessons_completed else 0,
            "last_activity": prog.last_activity_at.isoformat() if prog and prog.last_activity_at else None,
        })
    return {"course_id": str(course_id), "modules": progress}


@router.delete("/{course_id}/leave", status_code=204)
async def leave_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == user.id,
        )
    )
    enr = result.scalar_one_or_none()
    if not enr:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")
    await db.delete(enr)
    await db.commit()


@router.get("/{course_id}/leaderboard")
async def get_course_leaderboard(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Internal course leaderboard — shows XP ranking among enrolled students.
    Only visible to enrolled students and the course teacher.
    """
    # Check access (enrolled or teacher)
    course = (await db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")

    is_teacher = str(course.teacher_id) == str(user.id) or user.role == "admin"
    if not is_teacher:
        enrollment = (await db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.student_id == user.id,
                CourseEnrollment.status == "active",
            )
        )).scalar_one_or_none()
        if not enrollment:
            raise HTTPException(403, "You are not enrolled in this course")

    # Get all enrolled students sorted by XP
    rows = (await db.execute(
        select(User, CourseEnrollment.enrolled_at)
        .join(CourseEnrollment, CourseEnrollment.student_id == User.id)
        .where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.status == "active",
        )
        .order_by(User.xp.desc())
        .limit(50)
    )).all()

    my_rank = None
    entries = []
    for rank, (student, enrolled_at) in enumerate(rows, 1):
        is_me = str(student.id) == str(user.id)
        if is_me:
            my_rank = rank
        entries.append({
            "rank": rank,
            "name": f"{student.first_name or ''} {student.last_name or ''}".strip() or "Anonymous",
            "xp": student.xp,
            "level": student.level,
            "streak_days": student.streak_days or 0,
            "is_me": is_me,
            "enrolled_at": enrolled_at.isoformat() if enrolled_at else None,
        })

    return {
        "course_id": str(course_id),
        "course_title": course.title,
        "my_rank": my_rank,
        "total_students": len(entries),
        "leaderboard": entries,
    }
