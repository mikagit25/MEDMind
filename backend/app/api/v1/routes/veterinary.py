"""Veterinary mode routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User
from app.services.vet_service import (
    get_all_species,
    get_dosing_for_drug_species,
    check_species_safety,
)

router = APIRouter(prefix="/veterinary", tags=["veterinary"])


class SpeciesOut(BaseModel):
    id: UUID
    name: str
    name_ru: str | None
    scientific_name: str | None
    category: str | None
    icon: str | None

    model_config = {"from_attributes": True}


class DosingOut(BaseModel):
    route: str | None
    dose: str | None
    frequency: str | None
    max_dose: str | None
    is_toxic: bool
    toxicity_note: str | None
    notes: str | None
    source: str | None

    model_config = {"from_attributes": True}


class SafetyCheckRequest(BaseModel):
    drug_id: UUID
    species_id: UUID


@router.get("/species", response_model=list[SpeciesOut])
async def list_species(db: AsyncSession = Depends(get_db)):
    """List all animal species available in veterinary mode."""
    return await get_all_species(db)


@router.get("/drugs/{drug_id}/dosing/{species_id}", response_model=list[DosingOut])
async def get_drug_dosing(
    drug_id: UUID,
    species_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get species-specific dosing for a drug."""
    entries = await get_dosing_for_drug_species(db, drug_id, species_id)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail="No dosing information found for this drug/species combination.",
        )
    return entries


@router.post("/drugs/check-species-safety")
async def check_drug_species_safety(
    data: SafetyCheckRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check if a drug is safe for a given animal species."""
    return await check_species_safety(db, data.drug_id, data.species_id)


@router.get("/zoonoses")
async def get_zoonoses(user: User = Depends(get_current_user)):
    """List common zoonotic diseases (educational reference)."""
    return {
        "zoonoses": [
            {
                "name": "Rabies",
                "name_ru": "Бешенство",
                "pathogen": "Lyssavirus",
                "transmission": "Bite from infected animal",
                "species": ["Dog", "Cat", "Bat", "Fox"],
                "prevention": "Pre-exposure prophylaxis, post-exposure vaccination",
            },
            {
                "name": "Leptospirosis",
                "name_ru": "Лептоспироз",
                "pathogen": "Leptospira spp.",
                "transmission": "Contact with infected urine/water",
                "species": ["Rat", "Dog", "Cattle"],
                "prevention": "Vaccination, avoid contaminated water",
            },
            {
                "name": "Toxoplasmosis",
                "name_ru": "Токсоплазмоз",
                "pathogen": "Toxoplasma gondii",
                "transmission": "Cat feces, undercooked meat",
                "species": ["Cat"],
                "prevention": "Hygiene, avoid raw meat during pregnancy",
            },
            {
                "name": "Brucellosis",
                "name_ru": "Бруцеллёз",
                "pathogen": "Brucella spp.",
                "transmission": "Contact with infected animals/unpasteurized dairy",
                "species": ["Cattle", "Dog", "Sheep"],
                "prevention": "Pasteurization, animal vaccination",
            },
            {
                "name": "Q Fever",
                "name_ru": "Лихорадка Ку",
                "pathogen": "Coxiella burnetii",
                "transmission": "Inhaled aerosols from birthing fluids",
                "species": ["Sheep", "Cattle", "Cat"],
                "prevention": "Protective equipment, vaccination",
            },
        ]
    }


@router.put("/user/veterinary-settings")
async def update_vet_settings(
    enabled: bool,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enable or disable veterinary mode for the current user."""
    prefs = user.preferences or {}
    prefs["vet_mode"] = enabled
    user.preferences = prefs
    await db.commit()
    return {"vet_mode": enabled, "detail": f"Veterinary mode {'enabled' if enabled else 'disabled'}"}
