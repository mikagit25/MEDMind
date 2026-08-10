"""
CLI script to assign a local reviewer for Gulf jurisdiction MCQ review.

Usage:
    python -m app.scripts.assign_reviewer --email user@example.com --jurisdictions sa ae_dubai
    python -m app.scripts.assign_reviewer --email user@example.com --jurisdictions sa --name "Dr. Ahmed Al-Rashidi" --license-country "Saudi Arabia" --license-number "SCH-12345"
    python -m app.scripts.assign_reviewer --list

Jurisdictions available:
    sa        — Saudi Arabia (SCFHS/SNLE)
    ae_dubai  — Dubai (DHA)
    ae_abudhabi — Abu Dhabi (DOH/HAAD)
    qa        — Qatar (QCHP)
    om        — Oman (OMSB/MOH)
    bh        — Bahrain (NHRA)
    ae_moh    — UAE Northern Emirates (MOHAP)
    kw        — Kuwait (MOH-KW)
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models.models import User, Reviewer

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

VALID_JURISDICTIONS = {
    "sa": "Saudi Arabia (SCFHS/SNLE)",
    "ae_dubai": "Dubai (DHA)",
    "ae_abudhabi": "Abu Dhabi (DOH/HAAD)",
    "qa": "Qatar (QCHP)",
    "om": "Oman (OMSB/MOH)",
    "bh": "Bahrain (NHRA)",
    "ae_moh": "UAE Northern Emirates (MOHAP)",
    "kw": "Kuwait (MOH-KW)",
}


async def list_reviewers(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.role == "reviewer"))
    users = result.scalars().all()
    if not users:
        print("No users with reviewer role found.")
        return
    print(f"\n{'Email':<40} {'Name':<30} {'Jurisdictions'}")
    print("-" * 90)
    for u in users:
        slug = u.email.split("@")[0]
        rev_result = await db.execute(select(Reviewer).where(Reviewer.slug == slug))
        rev = rev_result.scalar_one_or_none()
        jurisdictions = rev.jurisdictions if rev else []
        name = f"{u.first_name or ''} {u.last_name or ''}".strip() or "(no name)"
        print(f"{u.email:<40} {name:<30} {jurisdictions}")


async def assign_reviewer(
    db: AsyncSession,
    email: str,
    jurisdictions: list[str],
    name: str | None,
    license_country: str | None,
    license_number: str | None,
) -> None:
    # Validate jurisdictions
    invalid = [j for j in jurisdictions if j not in VALID_JURISDICTIONS]
    if invalid:
        logger.error(f"Invalid jurisdiction codes: {invalid}")
        logger.error(f"Valid codes: {list(VALID_JURISDICTIONS.keys())}")
        sys.exit(1)

    # Find user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        logger.error(f"User not found: {email}")
        logger.error("Create the user account first via /auth/register or admin panel.")
        sys.exit(1)

    # Set reviewer role
    old_role = user.role
    user.role = "reviewer"
    logger.info(f"User {email}: role {old_role!r} → 'reviewer'")

    # Find or create Reviewer record (slug = email prefix)
    slug = email.split("@")[0]
    rev_result = await db.execute(select(Reviewer).where(Reviewer.slug == slug))
    reviewer = rev_result.scalar_one_or_none()

    display_name = name or f"{user.first_name or ''} {user.last_name or ''}".strip() or email.split("@")[0]

    if not reviewer:
        reviewer = Reviewer(
            slug=slug,
            name=display_name,
            is_active=True,
        )
        db.add(reviewer)
        logger.info(f"Created Reviewer record: slug={slug!r}, name={display_name!r}")
    else:
        if name:
            reviewer.name = name
        logger.info(f"Updating existing Reviewer record: slug={slug!r}")

    reviewer.jurisdictions = jurisdictions
    if license_country:
        reviewer.license_country = license_country
    if license_number:
        reviewer.license_number = license_number

    await db.commit()

    logger.info(f"\n✅ Reviewer assigned:")
    logger.info(f"   Email:       {email}")
    logger.info(f"   Name:        {reviewer.name}")
    logger.info(f"   Slug:        {slug}")
    logger.info(f"   Jurisdictions: {jurisdictions}")
    if license_country:
        logger.info(f"   Country:     {license_country}")
    if license_number:
        logger.info(f"   Licence #:   {license_number}")
    logger.info(f"\nThe reviewer can now access:")
    logger.info(f"   GET  /reviewer/queue/jurisdiction?jurisdiction={jurisdictions[0]}")
    logger.info(f"   POST /reviewer/submit-jurisdiction/{{question_id}}")
    for j in jurisdictions:
        logger.info(f"   Authorized for: {VALID_JURISDICTIONS[j]}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Assign local reviewer for Gulf MCQ jurisdiction review")
    parser.add_argument("--email", type=str, help="User email to promote to reviewer")
    parser.add_argument(
        "--jurisdictions", nargs="+", metavar="CODE",
        help=f"Jurisdiction codes: {list(VALID_JURISDICTIONS.keys())}"
    )
    parser.add_argument("--name", type=str, default=None, help="Display name for reviewer profile")
    parser.add_argument("--license-country", type=str, default=None, help="Country where nurse is licensed")
    parser.add_argument("--license-number", type=str, default=None, help="Licence/registration number")
    parser.add_argument("--list", action="store_true", help="List all existing reviewers")
    args = parser.parse_args()

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sm() as db:
        if args.list:
            await list_reviewers(db)
        elif args.email and args.jurisdictions:
            await assign_reviewer(
                db,
                email=args.email,
                jurisdictions=args.jurisdictions,
                name=args.name,
                license_country=args.license_country,
                license_number=args.license_number,
            )
        else:
            parser.print_help()
            print("\nExamples:")
            print("  python -m app.scripts.assign_reviewer --list")
            print("  python -m app.scripts.assign_reviewer --email nurse@example.com --jurisdictions sa")
            print("  python -m app.scripts.assign_reviewer --email dr@example.com --jurisdictions sa ae_dubai --name 'Dr. Ahmed' --license-country 'Saudi Arabia' --license-number 'SCH-12345'")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
