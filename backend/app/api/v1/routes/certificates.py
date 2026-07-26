"""Certificates — module completion PDF certificates (V5 Phase 6).

Endpoints:
  POST   /certificates/issue/{module_id}     — issue cert (idempotent; requires completion or score ≥ threshold)
  GET    /certificates/my                    — list user's certificates
  GET    /certificates/{cert_id}/download    — stream PDF
  PATCH  /certificates/{cert_id}/hide-name  — toggle name visibility (opt-out)
  GET    /certificates/verify/{code}         — public verification (no auth)
"""
from __future__ import annotations

import io
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_optional, get_db
from app.models.models import Certificate, Module, User, UserProgress

router = APIRouter(prefix="/certificates", tags=["certificates"])

CERT_PASS_THRESHOLD = 70.0   # minimum MCQ score (%) to earn a certificate
LOGO_TEXT = "MedMind AI"     # shown in PDF header instead of image file


# ── PDF generation ────────────────────────────────────────────────────────────

def _generate_pdf(
    user_name: str,
    module_title: str,
    duration_hours: float,
    score: Optional[float],
    issued_at: datetime,
    verification_code: str,
    language: str = "en",
) -> bytes:
    """Generate a certificate PDF using reportlab and return bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    W, _ = A4
    styles = {
        "brand": ParagraphStyle(
            "brand",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=colors.HexColor("#2563eb"),
            spaceAfter=4,
        ),
        "headline": ParagraphStyle(
            "headline",
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=colors.HexColor("#111827"),
            spaceAfter=8,
            leading=34,
        ),
        "sub": ParagraphStyle(
            "sub",
            fontName="Helvetica",
            fontSize=13,
            textColor=colors.HexColor("#374151"),
            spaceAfter=4,
            leading=18,
        ),
        "name": ParagraphStyle(
            "name",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=colors.HexColor("#111827"),
            spaceAfter=6,
        ),
        "module": ParagraphStyle(
            "module",
            fontName="Helvetica-Bold",
            fontSize=17,
            textColor=colors.HexColor("#2563eb"),
            spaceAfter=4,
            leading=22,
        ),
        "meta": ParagraphStyle(
            "meta",
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#6b7280"),
            spaceAfter=2,
        ),
        "code": ParagraphStyle(
            "code",
            fontName="Courier",
            fontSize=9,
            textColor=colors.HexColor("#9ca3af"),
        ),
    }

    date_str = issued_at.strftime("%B %d, %Y")
    hours_str = f"{duration_hours:.1f}" if duration_hours else "—"
    score_str = f"{score:.0f}%" if score is not None else "—"

    divider = lambda: [
        Spacer(1, 6 * mm),
        Paragraph('<hr width="100%" color="#e5e7eb" thickness="1"/>', styles["meta"]),
        Spacer(1, 6 * mm),
    ]

    story = [
        Paragraph(LOGO_TEXT, styles["brand"]),
        Spacer(1, 8 * mm),
        Paragraph("Certificate of Completion", styles["headline"]),
        Paragraph("This certifies that", styles["sub"]),
        Spacer(1, 2 * mm),
        Paragraph(user_name, styles["name"]),
        Spacer(1, 2 * mm),
        Paragraph("has successfully completed the module", styles["sub"]),
        Spacer(1, 2 * mm),
        Paragraph(module_title, styles["module"]),
        *divider(),
        Paragraph(f"Date issued: {date_str}", styles["meta"]),
        Paragraph(f"Duration: {hours_str} hours", styles["meta"]),
        Paragraph(f"Assessment score: {score_str}", styles["meta"]),
        Spacer(1, 10 * mm),
        Paragraph(
            "This certificate is for educational purposes only and does not constitute "
            "a medical licence or professional qualification.",
            styles["meta"],
        ),
        Spacer(1, 6 * mm),
        Paragraph(f"Verification code: {verification_code}", styles["code"]),
        Paragraph(f"Verify at: medmind.ai/verify/{verification_code}", styles["code"]),
    ]

    doc.build(story)
    return buf.getvalue()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cert_out(cert: Certificate) -> dict:
    mod = cert.module
    return {
        "id": str(cert.id),
        "module_id": str(cert.module_id),
        "module_title": mod.title if mod else "",
        "verification_code": cert.verification_code,
        "score": float(cert.score) if cert.score is not None else None,
        "issued_at": cert.issued_at.isoformat() if cert.issued_at else None,
        "language": cert.language,
        "hide_name": cert.hide_name,
        "duration_hours": float(mod.duration_hours) if mod and mod.duration_hours else 0,
        "linkedin_url": (
            f"https://www.linkedin.com/profile/add?startTask=CERTIFICATION_NAME"
            f"&name={mod.title.replace(' ', '+') if mod else 'MedMind+Certificate'}"
            f"&organizationId=medmind"
            f"&issueYear={cert.issued_at.year if cert.issued_at else ''}"
            f"&issueMonth={cert.issued_at.month if cert.issued_at else ''}"
            f"&certUrl=https://medmind.ai/verify/{cert.verification_code}"
        ),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/issue/{module_id}", status_code=201)
async def issue_certificate(
    module_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue (or return existing) certificate for a completed module."""
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Check eligibility: module completed OR MCQ score meets threshold
    progress = (await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == current_user.id,
            UserProgress.module_id == module_id,
        )
    )).scalar_one_or_none()

    score: Optional[float] = None
    if progress:
        score = float(progress.mcq_score) if progress.mcq_score is not None else None
        completed = float(progress.completion_percent or 0) >= 100
        score_ok = score is not None and score >= CERT_PASS_THRESHOLD
        if not (completed or score_ok):
            raise HTTPException(
                status_code=422,
                detail=f"Module not completed. Need 100% completion or MCQ score ≥ {CERT_PASS_THRESHOLD}%.",
            )
    else:
        raise HTTPException(status_code=422, detail="No progress found for this module.")

    # Idempotent — return existing cert
    existing = (await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.module), selectinload(Certificate.user))
        .where(
            Certificate.user_id == current_user.id,
            Certificate.module_id == module_id,
        )
    )).scalar_one_or_none()

    if existing:
        return {**_cert_out(existing), "already_issued": True}

    # Generate new certificate
    verification_code = secrets.token_hex(12).upper()   # 24-char hex
    lang = (current_user.preferences or {}).get("language") or "en"

    cert = Certificate(
        user_id=current_user.id,
        module_id=module_id,
        verification_code=verification_code,
        score=score,
        issued_at=datetime.now(timezone.utc).replace(tzinfo=None),
        language=lang,
    )
    db.add(cert)
    await db.commit()

    cert = (await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.module), selectinload(Certificate.user))
        .where(Certificate.id == cert.id)
    )).scalar_one()

    return {**_cert_out(cert), "already_issued": False}


@router.get("/my")
async def list_my_certificates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all certificates earned by the current user."""
    rows = (await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.module), selectinload(Certificate.user))
        .where(Certificate.user_id == current_user.id)
        .order_by(Certificate.issued_at.desc())
    )).scalars().all()

    return {"certificates": [_cert_out(c) for c in rows], "total": len(rows)}


@router.get("/verify/{code}")
async def verify_certificate(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — verify a certificate by code (no auth required)."""
    cert = (await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.user), selectinload(Certificate.module))
        .where(Certificate.verification_code == code.upper())
    )).scalar_one_or_none()

    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    user: User = cert.user
    module: Module = cert.module

    name: Optional[str] = None
    if not cert.hide_name and user:
        name = " ".join(filter(None, [user.first_name, user.last_name])) or None

    return {
        "valid": True,
        "name": name,
        "module_title": module.title if module else "",
        "issued_at": cert.issued_at.isoformat() if cert.issued_at else None,
        "score": float(cert.score) if cert.score is not None else None,
        "duration_hours": float(module.duration_hours) if module and module.duration_hours else 0,
    }


@router.get("/{cert_id}/download")
async def download_certificate(
    cert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a certificate as PDF."""
    cert = (await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.user), selectinload(Certificate.module))
        .where(
            Certificate.id == cert_id,
            Certificate.user_id == current_user.id,
        )
    )).scalar_one_or_none()

    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    user: User = cert.user
    module: Module = cert.module

    user_name = " ".join(filter(None, [user.first_name, user.last_name])) if user else "Learner"
    module_title = module.title if module else "Medical Module"
    duration_hours = float(module.duration_hours) if module and module.duration_hours else 0

    pdf_bytes = _generate_pdf(
        user_name=user_name,
        module_title=module_title,
        duration_hours=duration_hours,
        score=float(cert.score) if cert.score is not None else None,
        issued_at=cert.issued_at or datetime.utcnow(),
        verification_code=cert.verification_code,
        language=cert.language,
    )

    safe_title = "".join(c if (c.isalnum() and c.isascii()) or c in " _-" else "_" for c in module_title)[:50]
    safe_title = safe_title.strip("_ -") or "Certificate"
    filename = f"MedMind_Certificate_{safe_title}.pdf"
    from urllib.parse import quote as _quote
    filename_star = _quote(filename, safe="")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename_star}"},
    )


@router.patch("/{cert_id}/hide-name", status_code=200)
async def toggle_hide_name(
    cert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle whether the user's name is shown on public verification page."""
    cert = (await db.execute(
        select(Certificate).where(
            Certificate.id == cert_id,
            Certificate.user_id == current_user.id,
        )
    )).scalar_one_or_none()

    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    cert.hide_name = not cert.hide_name
    await db.commit()
    return {"hide_name": cert.hide_name}
