"""
Notification helper — create a DB notification and push to SSE stream.

Usage:
    from app.core.notify import send_notification

    await send_notification(
        db, user_id=student.id,
        type="achievement",
        title="New Achievement!",
        body="You earned the '10 Lessons' badge.",
        data={"achievement_code": "lessons_10"},
    )
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notification


async def send_notification(
    db: AsyncSession,
    user_id: UUID,
    type: str,
    title: str,
    body: str,
    data: Optional[dict[str, Any]] = None,
) -> Notification:
    """Persist a notification and push it to any open SSE streams."""
    n = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        data=data or {},
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(n)
    await db.flush()  # get ID without full commit

    # Push to SSE (non-blocking, best-effort)
    try:
        from app.api.v1.routes.notifications import push_notification
        await push_notification(str(user_id), {
            "type": "notification",
            "id": str(n.id),
            "notif_type": type,
            "title": title,
            "body": body,
            "data": data or {},
            "created_at": n.created_at.isoformat(),
        })
    except Exception:
        pass  # SSE push failure must never break the main flow

    return n
