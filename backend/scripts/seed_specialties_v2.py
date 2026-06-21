"""
Seed missing specialties: Pulmonology, Nephrology, Gastroenterology,
Endocrinology, Rheumatology, Infectious Diseases, Emergency Medicine,
Critical Care, Hematology, Ophthalmology, ENT, Orthopedics,
Psychiatry (dedicated), Oncology (dedicated), Dermatology (dedicated),
Anesthesiology (dedicated).

Idempotent — safe to run multiple times.

Usage:
    cd /opt/medmind/backend && python3 scripts/seed_specialties_v2.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.models import Specialty

NEW_SPECIALTIES = [
    {"code": "pulmonology",        "name": "Пульмонология",                "name_en": "Pulmonology",
     "icon": "🫁", "color": "#3B82F6", "description": "Respiratory medicine"},
    {"code": "nephrology",         "name": "Нефрология",                   "name_en": "Nephrology",
     "icon": "🫘", "color": "#8B5CF6", "description": "Kidney diseases"},
    {"code": "gastroenterology",   "name": "Гастроэнтерология",            "name_en": "Gastroenterology",
     "icon": "🫃", "color": "#10B981", "description": "GI and liver diseases"},
    {"code": "endocrinology",      "name": "Эндокринология",               "name_en": "Endocrinology",
     "icon": "🧬", "color": "#F59E0B", "description": "Hormonal and metabolic disorders"},
    {"code": "rheumatology",       "name": "Ревматология",                 "name_en": "Rheumatology",
     "icon": "🦴", "color": "#EF4444", "description": "Autoimmune and musculoskeletal diseases"},
    {"code": "infectious_diseases","name": "Инфекционные болезни",         "name_en": "Infectious Diseases",
     "icon": "🦠", "color": "#06B6D4", "description": "Infectious diseases and antimicrobials"},
    {"code": "emergency_medicine", "name": "Скорая и неотложная помощь",   "name_en": "Emergency Medicine",
     "icon": "🚑", "color": "#DC2626", "description": "Emergency and acute care"},
    {"code": "critical_care",      "name": "Реаниматология и ИТ",          "name_en": "Critical Care",
     "icon": "🏥", "color": "#7C3AED", "description": "Intensive care and critical illness"},
    {"code": "hematology",         "name": "Гематология",                  "name_en": "Hematology",
     "icon": "🩸", "color": "#B91C1C", "description": "Blood diseases and disorders"},
    {"code": "ophthalmology",      "name": "Офтальмология",                "name_en": "Ophthalmology",
     "icon": "👁️", "color": "#0284C7", "description": "Eye diseases"},
    {"code": "ent",                "name": "ЛОР-болезни",                  "name_en": "Otorhinolaryngology (ENT)",
     "icon": "👂", "color": "#0891B2", "description": "Ear, nose and throat diseases"},
    {"code": "orthopedics",        "name": "Ортопедия и травматология",    "name_en": "Orthopedics & Traumatology",
     "icon": "🦿", "color": "#78716C", "description": "Bone, joint and musculoskeletal surgery"},
    {"code": "psychiatry",         "name": "Психиатрия",                   "name_en": "Psychiatry",
     "icon": "🧠", "color": "#7C3AED", "description": "Mental health disorders"},
    {"code": "oncology",           "name": "Онкология",                    "name_en": "Oncology",
     "icon": "🔬", "color": "#6D28D9", "description": "Cancer diagnosis and treatment"},
    {"code": "dermatology",        "name": "Дерматология",                 "name_en": "Dermatology",
     "icon": "🩹", "color": "#F97316", "description": "Skin diseases"},
    {"code": "anesthesiology",     "name": "Анестезиология и реанимация",  "name_en": "Anesthesiology",
     "icon": "💉", "color": "#64748B", "description": "Anesthesia and perioperative care"},
]


async def seed():
    created = 0
    skipped = 0
    async with AsyncSessionLocal() as db:
        for spec_data in NEW_SPECIALTIES:
            result = await db.execute(
                select(Specialty).where(Specialty.code == spec_data["code"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                # Update name_en if missing
                if not existing.name_en and spec_data.get("name_en"):
                    existing.name_en = spec_data["name_en"]
                    await db.flush()
                skipped += 1
                print(f"  SKIP  {spec_data['code']:25s}  (already exists)")
                continue

            spec = Specialty(
                code=spec_data["code"],
                name=spec_data["name"],
                name_en=spec_data.get("name_en"),
                icon=spec_data.get("icon", "📚"),
                description=spec_data.get("description", ""),
                is_active=True,
            )
            db.add(spec)
            await db.flush()
            created += 1
            print(f"  ADD   {spec_data['code']:25s}  {spec_data['name_en']}")

        await db.commit()
    print(f"\nDone: {created} created, {skipped} skipped.")


if __name__ == "__main__":
    asyncio.run(seed())
