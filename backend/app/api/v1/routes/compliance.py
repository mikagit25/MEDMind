"""GDPR compliance routes — data export and account deletion."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import (
    User, UserProgress, AIConversation, AIConversationMessage,
    UserNote, UserBookmark, UserAchievement, FlashcardReview,
    RefreshToken, UserConsent, AuditLog,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])
log = logging.getLogger(__name__)


@router.get("/export-data")
async def export_user_data(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    GDPR Article 20 — Export all personal data for the current user.
    Returns a JSON document with all user data.
    """
    # Progress
    progress_result = await db.execute(
        select(UserProgress).where(UserProgress.user_id == user.id)
    )
    progress_rows = progress_result.scalars().all()

    # AI conversations
    conv_result = await db.execute(
        select(AIConversation).where(AIConversation.user_id == user.id)
    )
    conversations = conv_result.scalars().all()

    conv_data = []
    for conv in conversations:
        msg_result = await db.execute(
            select(AIConversationMessage).where(AIConversationMessage.conversation_id == conv.id)
        )
        messages = msg_result.scalars().all()
        conv_data.append({
            "id": str(conv.id),
            "specialty": conv.specialty,
            "mode": conv.mode,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        })

    # Notes
    notes_result = await db.execute(
        select(UserNote).where(UserNote.user_id == user.id)
    )
    notes = notes_result.scalars().all()

    # Bookmarks
    bm_result = await db.execute(
        select(UserBookmark).where(UserBookmark.user_id == user.id)
    )
    bookmarks = bm_result.scalars().all()

    # Achievements
    ach_result = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == user.id)
    )
    achievements = ach_result.scalars().all()

    # Consents
    consent_result = await db.execute(
        select(UserConsent).where(UserConsent.user_id == user.id)
    )
    consents = consent_result.scalars().all()

    export = {
        "export_generated_at": datetime.utcnow().isoformat(),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "subscription_tier": user.subscription_tier,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "profile_data": user.profile_data,
            "preferences": user.preferences,
            "xp": user.xp,
            "level": user.level,
            "streak_days": user.streak_days,
        },
        "progress": [
            {
                "module_id": str(p.module_id),
                "completion_percent": float(p.completion_percent or 0),
                "mcq_score": float(p.mcq_score or 0),
                "lessons_completed": [str(l) for l in (p.lessons_completed or [])],
                "last_activity_at": p.last_activity_at.isoformat() if p.last_activity_at else None,
            }
            for p in progress_rows
        ],
        "ai_conversations": conv_data,
        "notes": [
            {"content": n.content, "lesson_id": str(n.lesson_id) if n.lesson_id else None,
             "created_at": n.created_at.isoformat() if n.created_at else None}
            for n in notes
        ],
        "bookmarks": [
            {"module_id": str(b.module_id) if b.module_id else None,
             "lesson_id": str(b.lesson_id) if b.lesson_id else None,
             "created_at": b.created_at.isoformat() if b.created_at else None}
            for b in bookmarks
        ],
        "achievements": [
            {"achievement_code": a.achievement_code, "earned_at": a.earned_at.isoformat() if a.earned_at else None}
            for a in achievements
        ],
        "consents": [
            {"consent_type": c.consent_type, "granted": c.granted,
             "created_at": c.created_at.isoformat() if c.created_at else None}
            for c in consents
        ],
    }

    # Log the export for audit trail
    db.add(AuditLog(
        user_id=user.id,
        action="gdpr_data_export",
        resource_type="user",
        resource_id=str(user.id),
        details={"exported_at": datetime.utcnow().isoformat()},
    ))
    await db.commit()

    return JSONResponse(content=export)


@router.post("/delete-account", status_code=200)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    GDPR Article 17 — Right to erasure.
    Anonymises the account: clears PII, revokes tokens, marks inactive.
    Does NOT hard-delete to preserve referential integrity and audit logs.
    """
    user_id = user.id

    # Revoke all refresh tokens
    await db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user_id)
        .values(is_revoked=True)
    )

    # Anonymise PII fields
    user.email = f"deleted_{user_id}@anonymised.medmind"
    user.email_hash = None
    user.password_hash = None
    user.first_name = "Deleted"
    user.last_name = "User"
    user.avatar_url = None
    user.oauth_id = None
    user.oauth_provider = None
    user.profile_data = {}
    user.preferences = {}
    user.stripe_customer_id = None
    user.is_active = False

    # Log deletion
    db.add(AuditLog(
        user_id=user_id,
        action="gdpr_account_deletion",
        resource_type="user",
        resource_id=str(user_id),
        details={"deleted_at": datetime.utcnow().isoformat()},
    ))

    await db.commit()

    log.info("Account anonymised for user %s (GDPR deletion)", user_id)
    return {"detail": "Your account has been anonymised and all personal data removed."}


@router.get("/consents")
async def get_consents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current GDPR consent status for the user."""
    result = await db.execute(
        select(UserConsent).where(UserConsent.user_id == user.id)
    )
    consents = result.scalars().all()
    return [
        {
            "consent_type": c.consent_type,
            "granted": c.granted,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in consents
    ]


@router.post("/consents/{consent_type}")
async def update_consent(
    consent_type: str,
    granted: bool,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a specific GDPR consent."""
    valid_types = {"data_processing", "analytics", "marketing"}
    if consent_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid consent type. Must be one of: {valid_types}")

    result = await db.execute(
        select(UserConsent).where(
            UserConsent.user_id == user.id,
            UserConsent.consent_type == consent_type,
        )
    )
    consent = result.scalar_one_or_none()

    if consent is None:
        consent = UserConsent(user_id=user.id, consent_type=consent_type, granted=granted)
        db.add(consent)
    else:
        consent.granted = granted

    await db.commit()
    return {"consent_type": consent_type, "granted": granted}
