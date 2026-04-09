"""Drug service — interaction checking and dose calculation."""
import logging
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Drug, DrugInteraction

log = logging.getLogger(__name__)


async def check_interactions(
    db: AsyncSession,
    drug_ids: list[UUID],
) -> list[dict]:
    """
    Check all pairwise interactions for a list of drug IDs.
    Returns list of interaction records (may be empty if none found).
    """
    if len(drug_ids) < 2:
        return []

    results = []
    checked: set[tuple] = set()

    for i, a in enumerate(drug_ids):
        for b in drug_ids[i + 1:]:
            pair = (min(str(a), str(b)), max(str(a), str(b)))
            if pair in checked:
                continue
            checked.add(pair)

            result = await db.execute(
                select(DrugInteraction).where(
                    or_(
                        (DrugInteraction.drug_a_id == a) & (DrugInteraction.drug_b_id == b),
                        (DrugInteraction.drug_a_id == b) & (DrugInteraction.drug_b_id == a),
                    )
                )
            )
            interaction = result.scalar_one_or_none()

            if interaction:
                # Fetch drug names
                drug_a = await db.get(Drug, interaction.drug_a_id)
                drug_b = await db.get(Drug, interaction.drug_b_id)
                results.append({
                    "drug_a": drug_a.name if drug_a else str(interaction.drug_a_id),
                    "drug_b": drug_b.name if drug_b else str(interaction.drug_b_id),
                    "severity": interaction.severity,
                    "mechanism": interaction.mechanism,
                    "clinical_effect": interaction.clinical_effect,
                    "management": interaction.management,
                    "evidence_level": interaction.evidence_level,
                })

    return results


def calculate_dose(
    drug_name: str,
    weight_kg: float,
    age_years: float | None,
    renal_gfr: float | None,
    dose_per_kg: float,
    unit: str = "mg",
    max_dose: float | None = None,
) -> dict:
    """
    Calculate total dose based on weight and optional adjustments.

    Applies:
    - Paediatric dose: weight-based
    - Renal adjustment: linear reduction if GFR < 60
    - Max dose cap
    """
    if weight_kg <= 0:
        return {"error": "Weight must be greater than 0"}

    base_dose = dose_per_kg * weight_kg

    adjustments: list[str] = []

    # Renal adjustment
    renal_factor = 1.0
    if renal_gfr is not None and renal_gfr < 60:
        if renal_gfr < 15:
            renal_factor = 0.25
            adjustments.append("Severe renal impairment (GFR<15): dose reduced by 75%")
        elif renal_gfr < 30:
            renal_factor = 0.5
            adjustments.append("Moderate-severe renal impairment (GFR<30): dose reduced by 50%")
        elif renal_gfr < 60:
            renal_factor = 0.75
            adjustments.append("Mild-moderate renal impairment (GFR<60): dose reduced by 25%")

    adjusted_dose = base_dose * renal_factor

    # Cap at max dose
    capped = False
    if max_dose and adjusted_dose > max_dose:
        adjusted_dose = max_dose
        capped = True
        adjustments.append(f"Capped at maximum dose: {max_dose} {unit}")

    return {
        "drug": drug_name,
        "weight_kg": weight_kg,
        "dose_per_kg": dose_per_kg,
        "unit": unit,
        "base_dose": round(base_dose, 2),
        "adjusted_dose": round(adjusted_dose, 2),
        "renal_factor": renal_factor,
        "capped_at_max": capped,
        "adjustments": adjustments,
        "disclaimer": (
            "This calculation is for educational purposes only. "
            "Always verify dosing with official drug references and clinical judgment."
        ),
    }
