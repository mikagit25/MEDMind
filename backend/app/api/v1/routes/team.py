"""Team management for Clinic tier.

The Clinic subscription allows up to 10 team members under one admin account.
Team membership is stored in profile_data["team_id"] / profile_data["team_role"].

Endpoints
─────────
GET    /team                   — list team members (admin or member)
POST   /team/invite            — send email invite (admin only)
POST   /team/join/{token}      — accept invite
DELETE /team/members/{user_id} — remove member (admin only)
GET    /team/stats             — aggregate progress stats for the team
"""
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User, UserProgress, Module
from app.core.encryption import decrypt_email

router = APIRouter(prefix="/team", tags=["team"])

MAX_TEAM_MEMBERS = 10


def _require_clinic(user: User):
    if user.subscription_tier not in ("clinic", "lifetime") and user.role != "admin":
        raise HTTPException(403, "Clinic subscription required")


def _team_id(user: User) -> Optional[str]:
    return (user.profile_data or {}).get("team_id")


def _team_role(user: User) -> Optional[str]:
    return (user.profile_data or {}).get("team_role")


def _make_invite_token(admin_id: str, email: str) -> str:
    h = hashlib.sha256(f"team_invite:{admin_id}:{email}:{datetime.utcnow().date()}".encode()).hexdigest()
    return h[:32]


@router.get("")
async def list_team(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members of the current user's team."""
    tid = _team_id(user)
    if not tid:
        # User is not in a team — if they're on Clinic, create a team for them
        _require_clinic(user)
        tid = str(uuid.uuid4())
        user.profile_data = {**(user.profile_data or {}), "team_id": tid, "team_role": "admin"}
        await db.commit()
        await db.refresh(user)

    members = (await db.execute(
        select(User).where(
            User.profile_data["team_id"].astext == tid,
            User.is_active == True,
        )
    )).scalars().all()

    return {
        "team_id": tid,
        "my_role": _team_role(user) or "member",
        "member_count": len(members),
        "max_members": MAX_TEAM_MEMBERS,
        "members": [
            {
                "id": str(m.id),
                "name": f"{m.first_name or ''} {m.last_name or ''}".strip() or "Member",
                "email": decrypt_email(m.email) if m.email else "—",
                "role": (m.profile_data or {}).get("team_role", "member"),
                "subscription_tier": m.subscription_tier,
                "xp": m.xp,
                "level": m.level,
                "streak_days": m.streak_days,
                "joined_at": str((m.profile_data or {}).get("team_joined_at", "")),
            }
            for m in members
        ],
    }


class InviteBody(BaseModel):
    email: str


@router.post("/invite")
async def invite_member(
    body: InviteBody,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a team invite (admin only)."""
    _require_clinic(user)
    tid = _team_id(user)
    role = _team_role(user)

    if not tid or role != "admin":
        raise HTTPException(403, "Only team admin can invite members")

    # Count current members
    members = (await db.execute(
        select(func.count(User.id)).where(
            User.profile_data["team_id"].astext == tid,
            User.is_active == True,
        )
    )).scalar() or 0

    if members >= MAX_TEAM_MEMBERS:
        raise HTTPException(400, f"Team is full ({MAX_TEAM_MEMBERS} members max)")

    token = _make_invite_token(str(user.id), body.email)
    invite_url = f"https://medmind.pro/team/join?token={token}&team={tid}"
    admin_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "your colleague"

    # Store pending invite in admin's profile_data
    pd = user.profile_data or {}
    invites = pd.get("team_invites", {})
    invites[token] = {"email": body.email, "sent_at": datetime.utcnow().isoformat(), "team_id": tid}
    user.profile_data = {**pd, "team_invites": invites}
    await db.commit()

    # Send invite email
    try:
        from app.core.email import send_email
        background_tasks.add_task(
            send_email,
            to=body.email,
            subject=f"{admin_name} invited you to join MedMind team",
            body=(
                f"Hi,\n\n{admin_name} has invited you to join their MedMind Clinic team.\n\n"
                f"Click the link below to accept:\n{invite_url}\n\n"
                f"This invite expires in 7 days.\n\nMedMind AI"
            ),
        )
    except Exception:
        pass  # non-fatal

    return {"success": True, "invite_url": invite_url, "token": token}


@router.post("/join/{token}")
async def join_team(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a team invite."""
    # Find the admin who created this invite
    all_users = (await db.execute(select(User).where(User.is_active == True))).scalars().all()
    admin = None
    invite_data = None
    for u in all_users:
        invites = (u.profile_data or {}).get("team_invites", {})
        if token in invites:
            admin = u
            invite_data = invites[token]
            break

    if not admin or not invite_data:
        raise HTTPException(404, "Invalid or expired invite token")

    tid = invite_data["team_id"]
    sent_at = datetime.fromisoformat(invite_data["sent_at"])
    if (datetime.utcnow() - sent_at).days > 7:
        raise HTTPException(400, "Invite has expired")

    if _team_id(user):
        raise HTTPException(400, "You are already in a team")

    # Count members
    members = (await db.execute(
        select(func.count(User.id)).where(
            User.profile_data["team_id"].astext == tid,
        )
    )).scalar() or 0
    if members >= MAX_TEAM_MEMBERS:
        raise HTTPException(400, "Team is full")

    # Join team
    user.profile_data = {
        **(user.profile_data or {}),
        "team_id": tid,
        "team_role": "member",
        "team_joined_at": datetime.utcnow().isoformat(),
    }

    # Remove used invite
    pd = admin.profile_data or {}
    invites = pd.get("team_invites", {})
    invites.pop(token, None)
    admin.profile_data = {**pd, "team_invites": invites}

    await db.commit()
    return {"success": True, "message": "You have joined the team!"}


@router.delete("/members/{member_id}", status_code=204)
async def remove_member(
    member_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the team (admin only)."""
    tid = _team_id(user)
    if not tid or _team_role(user) != "admin":
        raise HTTPException(403, "Only team admin can remove members")

    member = (await db.execute(select(User).where(User.id == member_id))).scalar_one_or_none()
    if not member or (member.profile_data or {}).get("team_id") != tid:
        raise HTTPException(404, "Member not found in your team")

    if str(member.id) == str(user.id):
        raise HTTPException(400, "Admin cannot remove themselves")

    pd = member.profile_data or {}
    pd.pop("team_id", None)
    pd.pop("team_role", None)
    pd.pop("team_joined_at", None)
    member.profile_data = pd
    await db.commit()


@router.get("/stats")
async def team_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate learning stats for the entire team."""
    tid = _team_id(user)
    if not tid:
        raise HTTPException(403, "Not in a team")

    members = (await db.execute(
        select(User).where(
            User.profile_data["team_id"].astext == tid,
            User.is_active == True,
        )
    )).scalars().all()

    member_ids = [m.id for m in members]

    # Aggregate progress
    progress_agg = (await db.execute(
        select(
            UserProgress.user_id,
            func.count(UserProgress.module_id).label("modules_started"),
            func.sum(
                func.jsonb_array_length(UserProgress.lessons_completed)
            ).label("lessons_done"),
        )
        .where(UserProgress.user_id.in_(member_ids))
        .group_by(UserProgress.user_id)
    )).all()

    progress_map = {str(p.user_id): {"modules_started": p.modules_started, "lessons_done": int(p.lessons_done or 0)} for p in progress_agg}

    members_out = []
    for m in members:
        pg = progress_map.get(str(m.id), {})
        members_out.append({
            "id": str(m.id),
            "name": f"{m.first_name or ''} {m.last_name or ''}".strip() or "Member",
            "role": (m.profile_data or {}).get("team_role", "member"),
            "xp": m.xp,
            "level": m.level,
            "streak_days": m.streak_days,
            "modules_started": pg.get("modules_started", 0),
            "lessons_done": pg.get("lessons_done", 0),
        })

    members_out.sort(key=lambda x: x["xp"], reverse=True)

    return {
        "team_id": tid,
        "member_count": len(members),
        "total_xp": sum(m["xp"] for m in members_out),
        "total_lessons": sum(m["lessons_done"] for m in members_out),
        "avg_streak": round(sum(m["streak_days"] for m in members_out) / max(len(members_out), 1), 1),
        "members": members_out,
    }
