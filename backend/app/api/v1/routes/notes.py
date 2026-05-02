"""User notes routes — create/read/update/delete personal notes on lessons."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User, UserNote

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteCreate(BaseModel):
    content: str
    lesson_id: Optional[UUID] = None
    module_id: Optional[UUID] = None


class NoteUpdate(BaseModel):
    content: str


class NoteOut(BaseModel):
    id: UUID
    content: str
    lesson_id: Optional[UUID]
    module_id: Optional[UUID]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, note: UserNote) -> "NoteOut":
        return cls(
            id=note.id,
            content=note.content,
            lesson_id=note.lesson_id,
            module_id=note.module_id,
            created_at=note.created_at.isoformat() if note.created_at else "",
            updated_at=note.updated_at.isoformat() if note.updated_at else "",
        )


@router.get("", response_model=List[NoteOut])
async def list_notes(
    lesson_id: Optional[UUID] = None,
    module_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(UserNote).where(UserNote.user_id == user.id)
    if lesson_id:
        stmt = stmt.where(UserNote.lesson_id == lesson_id)
    elif module_id:
        stmt = stmt.where(UserNote.module_id == module_id)
    stmt = stmt.order_by(UserNote.updated_at.desc())
    result = await db.execute(stmt)
    notes = result.scalars().all()
    return [NoteOut.from_orm_obj(n) for n in notes]


@router.post("", response_model=NoteOut, status_code=201)
async def create_note(
    data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not data.content.strip():
        raise HTTPException(status_code=422, detail="Note content cannot be empty")
    note = UserNote(
        user_id=user.id,
        content=data.content.strip(),
        lesson_id=data.lesson_id,
        module_id=data.module_id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return NoteOut.from_orm_obj(note)


@router.patch("/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: UUID,
    data: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserNote).where(UserNote.id == note_id, UserNote.user_id == user.id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not data.content.strip():
        raise HTTPException(status_code=422, detail="Note content cannot be empty")
    note.content = data.content.strip()
    await db.commit()
    await db.refresh(note)
    return NoteOut.from_orm_obj(note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserNote).where(UserNote.id == note_id, UserNote.user_id == user.id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(note)
    await db.commit()
