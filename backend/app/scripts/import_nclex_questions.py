"""
Import generated NCLEX questions into the DB.
Reads Modules/nclex_qbank_NURSE-XXX.json files produced by generate_nclex_questions.py

Usage:
  python -m app.scripts.import_nclex_questions          # all files
  python -m app.scripts.import_nclex_questions NURSE-002 # specific module
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import Module, MCQQuestion

MODULES_DIR = (
    Path("/app/data/modules") if Path("/app/data/modules").exists()
    else Path(__file__).parents[4] / "Modules"
)
OUTPUT_DIR = Path("/tmp/nclex_output")
PREFIX = "nclex_qbank_"


async def import_module(module_code: str) -> tuple[int, int]:
    """Returns (imported, skipped)."""
    path = OUTPUT_DIR / f"{PREFIX}{module_code}.json"
    if not path.exists():
        print(f"  ✗ File not found: {path}")
        return 0, 0

    data = json.loads(path.read_text())
    questions = data.get("questions", [])

    async with AsyncSessionLocal() as session:
        # Find or create the module
        result = await session.execute(
            select(Module).where(Module.code == module_code)
        )
        module = result.scalar_one_or_none()
        if not module:
            title = data.get("module_title", module_code)
            module = Module(
                id=uuid.uuid4(),
                code=module_code,
                title=title,
                description=f"NCLEX question bank: {title}",
                level=1,
                module_type="specialty_module",
            )
            session.add(module)
            await session.flush()
            print(f"  ℹ Created module {module_code}: {title}")

        # Get existing question texts to avoid duplicates
        existing = await session.execute(
            select(MCQQuestion.question).where(MCQQuestion.module_id == module.id)
        )
        existing_texts = {row[0] for row in existing.fetchall()}

        imported = 0
        skipped = 0

        for q in questions:
            qtext = q.get("question", "")
            if not qtext or qtext in existing_texts:
                skipped += 1
                continue

            # Build MCQQuestion
            qtype = q.get("question_type", "mcq")
            options = q.get("options") or {}
            if not options and qtype != "calculation":
                skipped += 1
                continue

            mcq = MCQQuestion(
                id=uuid.uuid4(),
                module_id=module.id,
                question=qtext,
                options=options,
                correct=q.get("correct") or "A",
                explanation=q.get("explanation") or "",
                difficulty=q.get("difficulty", "medium"),
                tags=q.get("tags") or [],
                question_type=qtype,
                correct_answers=q.get("correct_answers"),
                correct_order=q.get("correct_order"),
                numeric_answer=float(q["numeric_answer"]) if q.get("numeric_answer") is not None else None,
                numeric_tolerance=float(q.get("numeric_tolerance") or 0.5),
                numeric_unit=q.get("numeric_unit"),
                partial_scoring=bool(q.get("partial_scoring", False)),
                # NCLEX tagging
                nclex_client_needs=q.get("nclex_client_needs"),
                cjmm_skill=q.get("cjmm_skill"),
                ngn_type=q.get("ngn_type"),
                bowtie_data=q.get("bowtie_data"),
                matrix_data=q.get("matrix_data"),
                # Phase 2: rationales
                rationales=q.get("rationales"),
                key_takeaway=q.get("key_takeaway"),
                test_taking_tip=q.get("test_taking_tip"),
            )
            session.add(mcq)
            existing_texts.add(qtext)
            imported += 1

        await session.commit()
        return imported, skipped


async def main():
    target = sys.argv[1:] if len(sys.argv) > 1 else None

    if target is None:
        files = sorted(OUTPUT_DIR.glob(f"{PREFIX}*.json"))
        target = [f.stem.replace(PREFIX, "") for f in files]

    if not target:
        print("No nclex_qbank_*.json files found in Modules/. Run generate_nclex_questions.py first.")
        return

    total_imported = 0
    total_skipped = 0

    for module_code in target:
        print(f"\n{module_code}:")
        imported, skipped = await import_module(module_code)
        print(f"  imported={imported}  skipped(dup/invalid)={skipped}")
        total_imported += imported
        total_skipped += skipped

    print(f"\n{'='*40}")
    print(f"  Total imported: {total_imported}")
    print(f"  Total skipped:  {total_skipped}")
    print(f"{'='*40}")


if __name__ == "__main__":
    asyncio.run(main())
