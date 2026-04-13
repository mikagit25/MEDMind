"""Student long-term memory endpoints.

GET  /memory/              — list own memories (filterable)
GET  /memory/stats         — summary counts by type/specialty
DELETE /memory/{id}        — soft-delete (GDPR)
PATCH  /memory/{id}/verify — mark as verified (instructor/admin only)
PATCH  /memory/{id}/deprecate — manually deprecate an outdated fact
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.audit import audit
from app.core.database import get_db
from app.models.models import StudentMemory, User

router = APIRouter(prefix="/memory", tags=["memory"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class MemoryOut(BaseModel):
    id: UUID
    memory_type: str
    content: str
    specialty: Optional[str]
    competency_level: Optional[str]
    species_context: Optional[str]
    confidence: float
    verified: bool
    importance_score: float
    access_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryStats(BaseModel):
    total: int
    by_type: dict[str, int]
    by_specialty: dict[str, int]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_own_memory(db: AsyncSession, user_id: UUID, memory_id: UUID) -> StudentMemory:
    result = await db.execute(
        select(StudentMemory).where(
            StudentMemory.id == memory_id,
            StudentMemory.user_id == user_id,
        )
    )
    mem = result.scalar_one_or_none()
    if not mem:
        raise HTTPException(404, "Memory not found")
    return mem


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[MemoryOut])
async def list_memories(
    specialty: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None),
    include_deprecated: bool = Query(False),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the current user's long-term memories."""
    stmt = select(StudentMemory).where(StudentMemory.user_id == user.id)
    if not include_deprecated:
        stmt = stmt.where(StudentMemory.deprecated == False)
    if specialty:
        stmt = stmt.where(StudentMemory.specialty == specialty)
    if memory_type:
        stmt = stmt.where(StudentMemory.memory_type == memory_type)
    stmt = stmt.order_by(StudentMemory.importance_score.desc(), StudentMemory.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/stats", response_model=MemoryStats)
async def memory_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Aggregated memory statistics for the current user."""
    rows = (
        await db.execute(
            select(StudentMemory).where(
                StudentMemory.user_id == user.id,
                StudentMemory.deprecated == False,
            )
        )
    ).scalars().all()

    by_type: dict[str, int] = {}
    by_specialty: dict[str, int] = {}
    for m in rows:
        by_type[m.memory_type] = by_type.get(m.memory_type, 0) + 1
        if m.specialty:
            by_specialty[m.specialty] = by_specialty.get(m.specialty, 0) + 1

    return MemoryStats(total=len(rows), by_type=by_type, by_specialty=by_specialty)


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft-delete a memory (GDPR right to erasure)."""
    mem = await _get_own_memory(db, user.id, memory_id)
    mem.deprecated = True
    mem.updated_at = datetime.utcnow()
    await audit(db, "memory_deleted", user_id=user.id, resource_id=memory_id)
    await db.commit()


@router.patch("/{memory_id}/verify", response_model=MemoryOut)
async def verify_memory(
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark a memory as verified (instructors and admins only)."""
    if user.role not in ("professor", "admin"):
        raise HTTPException(403, "Only instructors and admins can verify memories")

    result = await db.execute(select(StudentMemory).where(StudentMemory.id == memory_id))
    mem = result.scalar_one_or_none()
    if not mem:
        raise HTTPException(404, "Memory not found")

    mem.verified = True
    mem.confidence = min(mem.confidence + 0.2, 1.0)
    mem.updated_at = datetime.utcnow()
    await audit(db, "memory_verified", user_id=user.id, resource_id=memory_id)
    await db.commit()
    await db.refresh(mem)
    return mem


@router.patch("/{memory_id}/deprecate", response_model=MemoryOut)
async def deprecate_memory(
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually mark a memory as outdated/deprecated."""
    mem = await _get_own_memory(db, user.id, memory_id)
    mem.deprecated = True
    mem.updated_at = datetime.utcnow()
    await audit(db, "memory_deprecated", user_id=user.id, resource_id=memory_id)
    await db.commit()
    await db.refresh(mem)
    return mem
