"""Enterprise B2B leads — public demo request endpoint + admin management."""
import hashlib
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.models import EnterpriseLead, User

router = APIRouter(prefix="/enterprise", tags=["enterprise"])

_admin = Depends(require_admin())

# ── Constants ─────────────────────────────────────────────────────────────────

PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "mail.ru", "yandex.ru", "yandex.com",
    "protonmail.com", "proton.me", "aol.com", "live.com",
}

TEAM_SIZES   = {"1-10", "11-25", "26-100", "100+"}
USE_CASES    = {"Veterinary company", "Clinic or hospital", "University", "Association", "Other"}
LEAD_STATUSES = {"new", "contacted", "qualified", "closed"}

RATE_LIMIT_COUNT  = 3   # max requests per window
RATE_LIMIT_WINDOW = 3600  # 1 hour


# ── Schemas ───────────────────────────────────────────────────────────────────

class EnterpriseLeadIn(BaseModel):
    first_name: str
    last_name:  str
    email:      EmailStr
    company:    str
    job_title:  str
    team_size:  str
    use_case:   str
    message:    Optional[str] = None

    @field_validator("email")
    @classmethod
    def reject_personal_email(cls, v: str) -> str:
        domain = v.split("@")[-1].lower()
        if domain in PERSONAL_DOMAINS:
            raise ValueError("Please use your work email address")
        return v

    @field_validator("team_size")
    @classmethod
    def valid_team_size(cls, v: str) -> str:
        if v not in TEAM_SIZES:
            raise ValueError(f"team_size must be one of {TEAM_SIZES}")
        return v

    @field_validator("use_case")
    @classmethod
    def valid_use_case(cls, v: str) -> str:
        if v not in USE_CASES:
            raise ValueError(f"use_case must be one of {USE_CASES}")
        return v

    @field_validator("first_name", "last_name", "company", "job_title")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v


class LeadStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in LEAD_STATUSES:
            raise ValueError(f"status must be one of {LEAD_STATUSES}")
        return v


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _check_rate_limit(request: Request) -> None:
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        ip    = _client_ip(request)
        key   = f"enterprise_lead:{ip}"
        count = await redis.get(key)
        if count and int(count) >= RATE_LIMIT_COUNT:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — allow request


async def _record_request(request: Request) -> None:
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        ip    = _client_ip(request)
        key   = f"enterprise_lead:{ip}"
        pipe  = redis.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, RATE_LIMIT_WINDOW)
        await pipe.execute()
    except Exception:
        pass


# ── POST /enterprise/leads ────────────────────────────────────────────────────

@router.post("/leads", status_code=201)
async def submit_lead(
    payload: EnterpriseLeadIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Submit an enterprise demo request (public, rate-limited)."""
    await _check_rate_limit(request)

    ip = _client_ip(request)
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()

    lead = EnterpriseLead(
        id         = uuid.uuid4(),
        first_name = payload.first_name,
        last_name  = payload.last_name,
        email      = payload.email,
        company    = payload.company,
        job_title  = payload.job_title,
        team_size  = payload.team_size,
        use_case   = payload.use_case,
        message    = payload.message,
        ip_hash    = ip_hash,
        status     = "new",
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
    )
    db.add(lead)
    await db.commit()

    # Send notification email (fire-and-forget)
    try:
        from app.services.email_service import send_enterprise_lead_notification
        await send_enterprise_lead_notification(
            first_name = payload.first_name,
            last_name  = payload.last_name,
            email      = payload.email,
            company    = payload.company,
            job_title  = payload.job_title,
            team_size  = payload.team_size,
            use_case   = payload.use_case,
            message    = payload.message,
        )
    except Exception:
        pass  # Don't fail the request if email fails

    await _record_request(request)
    return {"success": True}


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/leads", dependencies=[_admin])
async def list_leads(
    status:   Optional[str] = Query(None),
    page:     int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List enterprise leads (admin only)."""
    q = select(EnterpriseLead).order_by(desc(EnterpriseLead.created_at))
    if status and status in LEAD_STATUSES:
        q = q.where(EnterpriseLead.status == status)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    leads  = result.scalars().all()

    return {
        "total": total,
        "page":  page,
        "items": [
            {
                "id":         str(l.id),
                "first_name": l.first_name,
                "last_name":  l.last_name,
                "email":      l.email,
                "company":    l.company,
                "job_title":  l.job_title,
                "team_size":  l.team_size,
                "use_case":   l.use_case,
                "message":    l.message,
                "status":     l.status,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ],
    }


@router.get("/leads/export.csv", dependencies=[_admin])
async def export_leads_csv(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export enterprise leads as CSV (admin only)."""
    import csv
    import io

    q = select(EnterpriseLead).order_by(desc(EnterpriseLead.created_at))
    if status and status in LEAD_STATUSES:
        q = q.where(EnterpriseLead.status == status)

    result = await db.execute(q)
    leads  = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "First Name", "Last Name", "Email", "Company", "Job Title", "Team Size", "Use Case", "Status", "Message"])
    for l in leads:
        writer.writerow([
            l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else "",
            l.first_name, l.last_name, l.email,
            l.company, l.job_title, l.team_size, l.use_case,
            l.status, l.message or "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=enterprise_leads.csv"},
    )


@router.patch("/leads/{lead_id}/status", dependencies=[_admin])
async def update_lead_status(
    lead_id: str,
    payload: LeadStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update lead status (admin only)."""
    result = await db.execute(
        select(EnterpriseLead).where(EnterpriseLead.id == uuid.UUID(lead_id))
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status     = payload.status
    lead.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "status": payload.status}
