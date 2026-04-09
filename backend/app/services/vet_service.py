"""Veterinary mode service — species-specific dosing, toxicity warnings."""
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AnimalSpecies, Drug, VeterinaryDosing

log = logging.getLogger(__name__)

# Drugs known to be toxic / contraindicated for common species.
# Key: lowercase drug name fragment, Value: {species_name: warning}
KNOWN_TOXICITIES: dict[str, dict[str, str]] = {
    "paracetamol": {
        "Cat": "FATAL: causes methaemoglobinaemia and hepatic necrosis. Absolutely contraindicated.",
        "Dog": "Toxic in overdose: hepatotoxicity. Use only under strict vet supervision.",
    },
    "acetaminophen": {
        "Cat": "FATAL: causes methaemoglobinaemia. Absolutely contraindicated.",
        "Dog": "Toxic in overdose.",
    },
    "ibuprofen": {
        "Cat": "Highly toxic: GI ulceration, acute renal failure. Contraindicated.",
        "Dog": "Toxic even at low doses: GI ulceration, renal failure. Contraindicated.",
    },
    "aspirin": {
        "Cat": "Very high risk: cats lack glucuronyl transferase. Use only q72h if at all.",
    },
    "xylitol": {
        "Dog": "FATAL: causes hypoglycaemia and liver failure.",
    },
    "metronidazole": {
        "Bird": "Use with caution — neurotoxicity at high doses.",
    },
    "permethrin": {
        "Cat": "FATAL: severe neurotoxicity. Contraindicated — never use dog flea products on cats.",
    },
    "ivermectin": {
        "Dog": "Toxic in Collies and MDR1-mutant breeds (ABCB1 mutation).",
    },
}


async def get_all_species(db: AsyncSession) -> list[AnimalSpecies]:
    result = await db.execute(select(AnimalSpecies).where(AnimalSpecies.is_active == True))
    return list(result.scalars().all())


async def get_species_by_id(db: AsyncSession, species_id: UUID) -> AnimalSpecies | None:
    result = await db.execute(select(AnimalSpecies).where(AnimalSpecies.id == species_id))
    return result.scalar_one_or_none()


async def get_dosing_for_drug_species(
    db: AsyncSession,
    drug_id: UUID,
    species_id: UUID,
) -> list[VeterinaryDosing]:
    result = await db.execute(
        select(VeterinaryDosing)
        .where(
            VeterinaryDosing.drug_id == drug_id,
            VeterinaryDosing.species_id == species_id,
        )
    )
    return list(result.scalars().all())


async def check_species_safety(
    db: AsyncSession,
    drug_id: UUID,
    species_id: UUID,
) -> dict:
    """
    Returns safety information for a drug + species combination.
    Checks:
      1. VeterinaryDosing.is_toxic flag in DB
      2. KNOWN_TOXICITIES hardcoded table
    """
    # Fetch drug name
    drug_result = await db.execute(select(Drug).where(Drug.id == drug_id))
    drug = drug_result.scalar_one_or_none()
    if not drug:
        return {"safe": None, "warnings": ["Drug not found"]}

    species_result = await db.execute(select(AnimalSpecies).where(AnimalSpecies.id == species_id))
    species = species_result.scalar_one_or_none()
    if not species:
        return {"safe": None, "warnings": ["Species not found"]}

    warnings: list[str] = []
    is_toxic = False

    # Check DB dosing entries
    dosing = await get_dosing_for_drug_species(db, drug_id, species_id)
    for entry in dosing:
        if entry.is_toxic:
            is_toxic = True
            if entry.toxicity_note:
                warnings.append(entry.toxicity_note)

    # Check hardcoded known toxicities
    drug_name_lower = (drug.generic_name or drug.name or "").lower()
    for fragment, species_map in KNOWN_TOXICITIES.items():
        if fragment in drug_name_lower:
            species_warning = species_map.get(species.name)
            if species_warning:
                is_toxic = True
                warnings.append(f"⚠️ {species.name}: {species_warning}")

    return {
        "drug_id": str(drug_id),
        "drug_name": drug.name,
        "species_id": str(species_id),
        "species_name": species.name,
        "is_toxic": is_toxic,
        "warnings": warnings,
        "dosing_entries": [
            {
                "route": d.route,
                "dose": d.dose,
                "frequency": d.frequency,
                "max_dose": d.max_dose,
                "notes": d.notes,
                "source": d.source,
            }
            for d in dosing
            if not d.is_toxic
        ],
    }
