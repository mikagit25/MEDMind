"""Notifications API."""
import asyncio
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Notification, User

router = APIRouter(prefix="/notifications", tags=["notifications"])

# ── In-memory SSE subscriber registry ─────────────────────────────────────
# Maps user_id (str) → list of asyncio.Queue
_subscribers: dict[str, list[asyncio.Queue]] = {}


def _register(user_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.setdefault(user_id, []).append(q)
    return q


def _unregister(user_id: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(user_id, [])
    if q in subs:
        subs.remove(q)


async def push_notification(user_id: str, payload: dict) -> None:
    """Push a notification event to all SSE subscribers for a user."""
    for q in list(_subscribers.get(str(user_id), [])):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        q = q.where(Notification.is_read == False)
    q = q.order_by(desc(Notification.created_at)).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    unread_count = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )).scalar() or 0

    return {
        "unread_count": unread_count,
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "data": n.data,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ],
    }


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    n = (await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )).scalar_one_or_none()

    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")

    n.is_read = True
    await db.commit()
    return {"id": str(n.id), "is_read": True}


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    n = (await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(n)
    await db.commit()
    return {"deleted": True}


@router.get("/stream")
async def notification_stream(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Server-Sent Events stream — delivers real-time notifications."""
    user_id = str(user.id)

    async def event_generator():
        q = _register(user_id)
        # Send current unread count immediately on connect
        unread = (await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id,
                Notification.is_read == False,
            )
        )).scalar() or 0
        yield f"data: {json.dumps({'type': 'init', 'unread_count': unread})}\n\n"

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"data: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive ping every 25s
                    yield ": ping\n\n"
        finally:
            _unregister(user_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
