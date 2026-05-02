"""Medical/Veterinary lesson publication validator.

Runs a set of safety and quality checks before a lesson can be published.
Returns a list of human-readable error strings; an empty list means the
lesson passes all checks and may be published.

Usage:
    from app.services.lesson_validator import validate_for_publication

    errors = await validate_for_publication(lesson, specialty_code)
    if errors:
        raise HTTPException(400, {"errors": errors})
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.models import Lesson

# Species that require extra dosing caution
_VET_SPECIES = {"canine", "feline", "equine", "bovine", "porcine", "ovine", "avian", "exotic"}

# Drugs that need an MDR1 warning when used in canines
_MDR1_SENSITIVE_DRUGS = {"ivermectin", "loperamide", "vincristine", "doxorubicin", "moxidectin"}

# Specialties that require minimum 2 guideline sources
_EVIDENCE_REQUIRED_SPECIALTIES = {
    "surgery", "pharmacology", "internal_medicine", "cardiology",
    "oncology", "anesthesiology", "emergency_medicine",
}

# Veterinary specialties — triggers species-dosing checks
_VET_SPECIALTIES = {"veterinary", "vet", "veterinary_medicine", "veterinary_surgery"}


async def validate_for_publication(lesson: "Lesson", specialty_code: str) -> list[str]:
    """Return list of blocking errors. Empty list = OK to publish."""
    errors: list[str] = []
    content = lesson.content or {}
    blocks = content.get("blocks", [])
    species = list(lesson.species_applicability or ["human"])
    specialty = (specialty_code or "").lower()

    # ── 1. Basic completeness ─────────────────────────────────────────────────
    if not lesson.title or len(lesson.title.strip()) < 3:
        errors.append("Lesson title must be at least 3 characters.")

    if not blocks:
        errors.append("Lesson must contain at least one content block.")

    learning_objectives = content.get("learning_objectives", [])
    if not learning_objectives:
        errors.append(
            "Lesson must have at least one learning objective. "
            "Add 'learning_objectives' to the content."
        )

    # ── 2. Image accessibility ────────────────────────────────────────────────
    for block in blocks:
        if block.get("type") == "image" and not block.get("alt_text"):
            bid = block.get("id", f"order={block.get('order', '?')}")
            errors.append(
                f"Image block [{bid}] is missing 'alt_text'. "
                "Alt text is required for accessibility compliance."
            )

    # ── 3. Clinical risk safety warnings ─────────────────────────────────────
    if lesson.clinical_risk_level == "high":
        has_warning = any(
            "warning" in (block.get("clinical_warning") or "").lower()
            or "warning" in str(block.get("content", "")).lower()
            for block in blocks
        )
        if not has_warning:
            errors.append(
                "High-risk lessons must contain explicit safety warnings in at least one block. "
                "Add 'clinical_warning' to the relevant block or include 'WARNING' in the content."
            )

    # ── 4. Veterinary species-dosing checks ───────────────────────────────────
    is_vet_lesson = any(s in _VET_SPECIES for s in species) or specialty in _VET_SPECIALTIES
    if is_vet_lesson:
        # Check for species-specific dosing info
        content_str = str(content).lower()
        has_dosing = (
            any(b.get("type") == "dosage_table" for b in blocks)
            or "dosage" in content_str
            or "dose" in content_str
            or "mg/kg" in content_str
        )
        # Only flag if lesson is about pharmacology/treatment (not pure anatomy)
        has_drug_context = any(
            kw in content_str
            for kw in ("drug", "medication", "antibiotic", "treatment", "dose", "dosing")
        )
        if has_drug_context and not has_dosing:
            errors.append(
                "Veterinary lessons with drug/treatment content must include species-specific "
                "dosing information. Add a 'dosage_table' block or include mg/kg dosing data."
            )

        # MDR1 gene mutation warning for ivermectin in canines
        if "canine" in species:
            for drug in _MDR1_SENSITIVE_DRUGS:
                if drug in content_str:
                    if "mdr1" not in content_str and "herding breed" not in content_str:
                        errors.append(
                            f"Lesson mentions '{drug}' for canines but does not warn about "
                            "MDR1 gene mutation sensitivity in Collies, Shelties, and other "
                            "herding breeds. Add an MDR1 warning block."
                        )
                    break  # one warning per lesson is enough

        # Cross-species comparative content requires an explicit flag
        if "human" in species and any(s in _VET_SPECIES for s in species):
            if not content.get("cross_species_comparative"):
                errors.append(
                    "This lesson mixes human and veterinary species. "
                    "Set 'cross_species_comparative: true' in the content to confirm this is "
                    "intentional, and add a 'cross_species_warning' to the lesson."
                )

    # ── 5. Evidence-based medicine — guideline sources ─────────────────────────
    if specialty in _EVIDENCE_REQUIRED_SPECIALTIES:
        sources = content.get("guideline_sources", [])
        if len(sources) < 2:
            errors.append(
                f"'{specialty}' specialty lessons require at least 2 authoritative guideline "
                "sources (e.g. WHO, AHA, NICE). Add them to 'guideline_sources' in the content."
            )

    # ── 6. Review currency ────────────────────────────────────────────────────
    if lesson.last_expert_review is not None:
        from datetime import datetime, timedelta
        age_days = (datetime.utcnow() - lesson.last_expert_review).days
        if age_days > 730:  # >2 years
            errors.append(
                f"This lesson was last expert-reviewed {age_days} days ago (>2 years). "
                "Clinical guidelines may have changed. Re-review before publishing."
            )

    return errors
