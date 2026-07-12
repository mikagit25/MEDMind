"""Role-based dashboard endpoints."""
import io
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.cache import get_cached, set_cached, invalidate
from app.models.models import (
    User, UserProgress, FlashcardReview, Flashcard, Lesson,
    Module, CMECredit, CourseEnrollment, Course, UserAchievement, LessonSrsItem,
)
from app.core.encryption import decrypt_email

STUDENT_DASHBOARD_TTL = 300  # 5 minutes

router = APIRouter(tags=["dashboard"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _base_stats(user: User, db: AsyncSession) -> Dict[str, Any]:
    """Shared stats — ORM-based aggregation (dialect-agnostic)."""
    # Count total lessons completed across all modules (sum list lengths via Python)
    progress_rows = (await db.execute(
        select(UserProgress.lessons_completed)
        .where(UserProgress.user_id == user.id)
    )).scalars().all()
    lessons_done = sum(
        len(lc) if isinstance(lc, list) else 0
        for lc in progress_rows
    )

    modules_started = (await db.execute(
        select(func.count()).select_from(UserProgress)
        .where(UserProgress.user_id == user.id)
    )).scalar() or 0

    due_cards = (await db.execute(
        select(func.count()).select_from(FlashcardReview)
        .where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.next_review_at <= datetime.utcnow(),
        )
    )).scalar() or 0

    ach_count = (await db.execute(
        select(func.count()).select_from(UserAchievement)
        .where(UserAchievement.user_id == user.id)
    )).scalar() or 0

    srs_due = (await db.execute(
        select(func.count()).select_from(LessonSrsItem).where(
            LessonSrsItem.user_id == user.id,
            LessonSrsItem.next_review_at <= datetime.utcnow(),
        )
    )).scalar() or 0

    return {
        "xp": user.xp,
        "level": user.level,
        "streak_days": user.streak_days or 0,
        "lessons_completed": lessons_done,
        "modules_started": int(modules_started),
        "flashcards_due": int(due_cards),
        "srs_due": int(srs_due),
        "achievements_count": int(ach_count),
    }


# ── Overview (all roles) ───────────────────────────────────────────────────────

@router.get("/dashboard/overview")
async def dashboard_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """General dashboard — works for any role."""
    stats = await _base_stats(user, db)

    # Recent modules
    prog_rows = (await db.execute(
        select(UserProgress, Module)
        .join(Module, Module.id == UserProgress.module_id)
        .where(UserProgress.user_id == user.id)
        .order_by(desc(UserProgress.last_activity_at))
        .limit(5)
    )).all()

    recent_modules = [
        {
            "id": str(p.module_id),
            "title": m.title,
            "title_en": m.title_en,
            "completion_percent": float(p.completion_percent or 0),
            "last_activity": p.last_activity_at.isoformat() if p.last_activity_at else None,
        }
        for p, m in prog_rows
    ]

    return {
        "role": user.role,
        "subscription_tier": user.subscription_tier,
        "stats": stats,
        "recent_modules": recent_modules,
    }


# ── Student dashboard ─────────────────────────────────────────────────────────

@router.get("/student/dashboard")
async def student_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cache_key = f"student_dashboard:{user.id}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    stats = await _base_stats(user, db)

    # Modules with lowest completion (weak areas to revisit)
    weak_mods = (await db.execute(
        select(UserProgress, Module)
        .join(Module, Module.id == UserProgress.module_id)
        .where(
            UserProgress.user_id == user.id,
            UserProgress.completion_percent < 80,
        )
        .order_by(UserProgress.completion_percent.asc())
        .limit(3)
    )).all()

    weak_areas = [
        {
            "id": str(p.module_id),
            "title": m.title,
            "completion_percent": float(p.completion_percent or 0),
        }
        for p, m in weak_mods
    ]

    # Today's plan: due flashcards + next lesson
    due_cards = (await db.execute(
        select(func.count(FlashcardReview.flashcard_id)).where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.next_review_at <= datetime.utcnow(),
        )
    )).scalar() or 0

    # Goals progress (daily_goal_minutes from preferences)
    prefs = user.preferences or {}
    daily_goal = prefs.get("daily_goal_minutes", 20)

    result = {
        "stats": stats,
        "weak_areas": weak_areas,
        "today_plan": {
            "flashcards_due": due_cards,
            "srs_due": stats.get("srs_due", 0),
            "reviews_due": due_cards + stats.get("srs_due", 0),
            "daily_goal_minutes": daily_goal,
            "suggested_action": "review_flashcards" if due_cards > 0 else "continue_module",
        },
    }
    await set_cached(cache_key, result, ttl=STUDENT_DASHBOARD_TTL)
    return result


# ── Doctor dashboard ──────────────────────────────────────────────────────────

@router.get("/doctor/dashboard")
async def doctor_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stats = await _base_stats(user, db)

    # CME credits summary
    cme_rows = (await db.execute(
        select(CMECredit).where(CMECredit.user_id == user.id)
        .order_by(desc(CMECredit.completion_date))
    )).scalars().all()

    total_cme = sum(float(c.credits_earned or 0) for c in cme_rows)
    recent_cme = [
        {
            "id": str(c.id),
            "activity_title": c.activity_title,
            "credits": float(c.credits_earned or 0),
            "credit_type": c.credit_type,
            "completed_at": c.completion_date.isoformat() if c.completion_date else None,
        }
        for c in cme_rows[:5]
    ]

    return {
        "stats": stats,
        "cme": {
            "total_credits": total_cme,
            "credits_this_year": sum(
                float(c.credits_earned or 0) for c in cme_rows
                if c.completion_date and c.completion_date.year == datetime.utcnow().year
            ),
            "recent": recent_cme,
        },
    }


# ── CME credits list ──────────────────────────────────────────────────────────

@router.get("/doctor/cme-credits")
async def get_cme_credits(
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(CMECredit, Module.title.label("module_title")).outerjoin(
        Module, Module.id == CMECredit.module_id
    ).where(CMECredit.user_id == user.id)

    if year:
        q = q.where(
            func.extract("year", CMECredit.completion_date) == year
        )

    q = q.order_by(desc(CMECredit.completion_date))
    rows = (await db.execute(q)).all()

    total = sum(float(r[0].credits_earned or 0) for r in rows)
    return {
        "total_credits": total,
        "year": year or "all",
        "credits": [
            {
                "id": str(r[0].id),
                "activity_title": r[0].activity_title,
                "module_title": r[1],
                "credits": float(r[0].credits_earned or 0),
                "credit_type": r[0].credit_type,
                "certificate_url": r[0].certificate_url,
                "completed_at": r[0].completion_date.isoformat() if r[0].completion_date else None,
            }
            for r in rows
        ],
    }


# ── Professor dashboard ───────────────────────────────────────────────────────

@router.get("/professor/dashboard")
async def professor_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stats = await _base_stats(user, db)

    # Courses created by this professor
    courses = (await db.execute(
        select(Course).where(Course.teacher_id == user.id, Course.is_active == True)
        .order_by(desc(Course.created_at))
    )).scalars().all()

    from app.models.models import CourseModule as CM
    courses_out = []
    for course in courses:
        # Count enrolled students
        student_count = (await db.execute(
            select(func.count(CourseEnrollment.id)).where(
                CourseEnrollment.course_id == course.id,
                CourseEnrollment.status == "active",
            )
        )).scalar() or 0

        module_count_c = (await db.execute(
            select(func.count(CM.id)).where(CM.course_id == course.id)
        )).scalar() or 0

        courses_out.append({
            "id": str(course.id),
            "title": course.title,
            "invite_code": course.invite_code,
            "student_count": student_count,
            "module_count": module_count_c,
            "is_active": course.is_active,
            "starts_at": course.starts_at.isoformat() if course.starts_at else None,
            "ends_at": course.ends_at.isoformat() if course.ends_at else None,
        })

    # Count total modules authored by this teacher
    from app.models.models import Module as Mod
    module_count = (await db.execute(
        select(func.count(Mod.id)).where(Mod.author_id == user.id)
    )).scalar() or 0

    return {
        # Flattened stats for frontend compatibility
        "xp": stats["xp"],
        "level": stats["level"],
        "streak_days": stats["streak_days"],
        "total_achievements": stats["achievements_count"],
        "total_modules": module_count,
        "courses": courses_out,
        "total_students": sum(c["student_count"] for c in courses_out),
    }


@router.get("/professor/students")
async def professor_all_students(
    search: Optional[str] = Query(None),
    course_id: Optional[str] = Query(None),
    sort: str = Query("enrolled_at"),   # enrolled_at | name | xp
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """All students across all professor's courses, with progress summary."""
    # Get all active courses for this professor
    courses = (await db.execute(
        select(Course).where(Course.teacher_id == user.id, Course.is_active == True)
    )).scalars().all()
    course_map = {str(c.id): c.title for c in courses}
    if not course_map:
        return {"students": [], "total": 0}

    course_ids = list(course_map.keys())
    if course_id and course_id in course_map:
        filter_ids = [course_id]
    else:
        filter_ids = course_ids

    # Fetch enrollments with student info
    q = (
        select(
            CourseEnrollment.student_id,
            CourseEnrollment.course_id,
            CourseEnrollment.enrolled_at,
            CourseEnrollment.status,
            User.first_name,
            User.last_name,
            User.email,
            User.xp,
            User.level,
            User.streak_days,
        )
        .join(User, User.id == CourseEnrollment.student_id)
        .where(CourseEnrollment.course_id.in_(filter_ids))
        .where(CourseEnrollment.status == "active")
    )
    if search:
        like = f"%{search.lower()}%"
        from sqlalchemy import or_
        q = q.where(or_(User.first_name.ilike(like), User.last_name.ilike(like), User.email.ilike(like)))

    rows = (await db.execute(q)).all()

    # Group by student (may appear in multiple courses)
    from collections import defaultdict
    student_data: dict = defaultdict(lambda: {
        "courses": [], "enrolled_at": None, "xp": 0, "level": 1, "streak_days": 0,
        "first_name": None, "last_name": None, "email": None,
    })
    for r in rows:
        sid = str(r.student_id)
        d = student_data[sid]
        d["courses"].append({"id": str(r.course_id), "title": course_map.get(str(r.course_id), "")})
        d["first_name"] = r.first_name
        d["last_name"] = r.last_name
        d["email"] = r.email
        d["xp"] = r.xp or 0
        d["level"] = r.level or 1
        d["streak_days"] = r.streak_days or 0
        if d["enrolled_at"] is None or (r.enrolled_at and r.enrolled_at < d["enrolled_at"]):
            d["enrolled_at"] = r.enrolled_at

    # Fetch last_activity per student from UserProgress
    if student_data:
        sids = list(student_data.keys())
        progress_rows = (await db.execute(
            select(
                UserProgress.user_id,
                func.max(UserProgress.last_activity).label("last_activity"),
                func.count(UserProgress.id).label("completions"),
            )
            .where(UserProgress.user_id.in_(sids))
            .group_by(UserProgress.user_id)
        )).all()
        for p in progress_rows:
            sid = str(p.user_id)
            if sid in student_data:
                student_data[sid]["last_activity"] = p.last_activity.isoformat() if p.last_activity else None
                student_data[sid]["completions"] = p.completions

    result = []
    for sid, d in student_data.items():
        name = " ".join(filter(None, [d["first_name"], d["last_name"]])) or "Student"
        result.append({
            "id": sid,
            "name": name,
            "email": decrypt_email(d["email"]) if d["email"] else "—",
            "courses": d["courses"],
            "xp": d["xp"],
            "level": d["level"],
            "streak_days": d["streak_days"],
            "completions": d.get("completions", 0),
            "last_activity": d.get("last_activity"),
            "enrolled_at": d["enrolled_at"].isoformat() if d.get("enrolled_at") else None,
        })

    # Sort
    if sort == "name":
        result.sort(key=lambda x: x["name"].lower())
    elif sort == "xp":
        result.sort(key=lambda x: x["xp"], reverse=True)
    else:
        result.sort(key=lambda x: x.get("enrolled_at") or "", reverse=True)

    return {"students": result, "total": len(result)}


# ── CME Certificate Generator ─────────────────────────────────────────────────

@router.get("/doctor/cme-credits/{credit_id}/certificate")
async def generate_cme_certificate(
    credit_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a professional PDF certificate for a CME activity."""
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
    from reportlab.graphics.shapes import Drawing, Rect, String as RLString
    import uuid as uuid_lib

    # Fetch the CME credit record
    row = (await db.execute(
        select(CMECredit, Module.title.label("mod_title"))
        .outerjoin(Module, Module.id == CMECredit.module_id)
        .where(CMECredit.id == credit_id, CMECredit.user_id == user.id)
    )).first()

    if not row:
        raise HTTPException(404, "Certificate not found")

    credit, mod_title = row

    # Generate deterministic certificate ID
    cert_seed = f"{credit.id}:{user.id}:{credit.completion_date}"
    cert_id = "MC-" + hashlib.sha256(cert_seed.encode()).hexdigest()[:12].upper()

    # Persist cert_id in certificate_url if not set
    if not credit.certificate_url:
        await db.execute(
            update(CMECredit).where(CMECredit.id == credit.id)
            .values(certificate_url=cert_id)
        )
        await db.commit()

    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Medical Professional"
    activity = credit.activity_title or mod_title or "Medical Education Activity"
    credits = float(credit.credits_earned or 1.0)
    credit_type = credit.credit_type or "AMA PRA Category 1"
    comp_date = credit.completion_date or datetime.utcnow()
    date_str = comp_date.strftime("%B %d, %Y")

    # ── Build PDF ─────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )

    NAVY   = colors.HexColor("#0f172a")
    BLUE   = colors.HexColor("#2563eb")
    GOLD   = colors.HexColor("#d97706")
    LIGHT  = colors.HexColor("#eff6ff")
    GRAY   = colors.HexColor("#64748b")

    styles = getSampleStyleSheet()
    center = lambda size, color=NAVY, bold=False: ParagraphStyle(
        "c", parent=styles["Normal"], alignment=1, fontSize=size,
        textColor=color, fontName="Helvetica-Bold" if bold else "Helvetica",
        leading=size*1.3, spaceAfter=0,
    )

    story = []

    # Header bar
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("MedMind AI", center(11, BLUE, bold=True)))
    story.append(Spacer(1, 0.2*cm))
    story.append(HRFlowable(width="100%", thickness=3, color=GOLD))
    story.append(Spacer(1, 0.5*cm))

    # Title
    story.append(Paragraph("CERTIFICATE OF COMPLETION", center(28, NAVY, bold=True)))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("Continuing Medical Education", center(13, GRAY)))
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.5*cm))

    # This is to certify
    story.append(Paragraph("This is to certify that", center(12, GRAY)))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"<b>{full_name}</b>", center(26, NAVY, bold=True)))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "has successfully completed the following Continuing Medical Education activity:",
        center(11, GRAY)
    ))
    story.append(Spacer(1, 0.4*cm))

    # Activity name box
    story.append(Paragraph(f"<i>{activity}</i>", center(17, BLUE)))
    story.append(Spacer(1, 0.5*cm))

    # Credits & date info table
    info = Table(
        [[
            Paragraph(f"<b>{credits:.1f}</b><br/><font size=9 color='#64748b'>{credit_type} Credits</font>", center(18, GOLD, bold=True)),
            Paragraph(f"<b>{date_str}</b><br/><font size=9 color='#64748b'>Completion Date</font>", center(14, NAVY)),
            Paragraph(f"<b>{cert_id}</b><br/><font size=9 color='#64748b'>Certificate ID</font>", center(10, GRAY)),
        ]],
        colWidths=[7*cm, 9*cm, 9*cm],
    )
    info.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT]),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
    ]))
    story.append(info)
    story.append(Spacer(1, 0.5*cm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"MedMind AI · medmind.pro · Issued {datetime.utcnow().strftime('%Y-%m-%d')} · Verify at medmind.pro/verify/{cert_id}",
        center(8, GRAY)
    ))

    doc.build(story)
    buf.seek(0)

    safe_name = full_name.replace(" ", "_")
    filename = f"CME_Certificate_{safe_name}_{comp_date.strftime('%Y%m')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
