"""Seed clinical algorithms from JSON data file.

Usage:
    cd backend && python -m app.scripts.seed_algorithms
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.models import ClinicalAlgorithm

DATA_FILE = Path(__file__).parent.parent / "data" / "clinical_algorithms_seed.json"


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        algorithms = json.load(f)

    async with SessionLocal() as db:
        inserted = 0
        updated = 0
        for item in algorithms:
            existing = (await db.execute(
                select(ClinicalAlgorithm).where(ClinicalAlgorithm.slug == item["slug"])
            )).scalar_one_or_none()

            if existing:
                for k, v in item.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                db.add(ClinicalAlgorithm(**item))
                inserted += 1

        await db.commit()
        print(f"Done: {inserted} inserted, {updated} updated")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
