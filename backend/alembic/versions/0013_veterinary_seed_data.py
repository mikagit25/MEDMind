"""Seed animal species for veterinary mode

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

SPECIES = [
    ("dog_id",   "Canine",  "Собака",    "Canis lupus familiaris",  "companion", "🐕"),
    ("cat_id",   "Feline",  "Кошка",     "Felis catus",             "companion", "🐈"),
    ("horse_id", "Equine",  "Лошадь",    "Equus caballus",          "livestock", "🐎"),
    ("cow_id",   "Bovine",  "Корова",    "Bos taurus",              "livestock", "🐄"),
    ("pig_id",   "Porcine", "Свинья",    "Sus scrofa domesticus",   "livestock", "🐖"),
    ("bird_id",  "Avian",   "Птица",     "Various",                 "avian",     "🦜"),
    ("rabbit_id","Rabbit",  "Кролик",    "Oryctolagus cuniculus",   "companion", "🐇"),
    ("exotic_id","Exotic",  "Экзотика",  "Various",                 "exotic",    "🦎"),
]

# Map var_name -> UUID (deterministic, generated once)
_UUIDS = {
    "dog_id":    "a1b2c3d4-0001-0001-0001-000000000001",
    "cat_id":    "a1b2c3d4-0001-0001-0001-000000000002",
    "horse_id":  "a1b2c3d4-0001-0001-0001-000000000003",
    "cow_id":    "a1b2c3d4-0001-0001-0001-000000000004",
    "pig_id":    "a1b2c3d4-0001-0001-0001-000000000005",
    "bird_id":   "a1b2c3d4-0001-0001-0001-000000000006",
    "rabbit_id": "a1b2c3d4-0001-0001-0001-000000000007",
    "exotic_id": "a1b2c3d4-0001-0001-0001-000000000008",
}


def upgrade():
    # Insert species (ignore conflicts — idempotent)
    conn = op.get_bind()

    for var, name, name_ru, sci, category, icon in SPECIES:
        sid = _UUIDS[var]
        conn.execute(
            sa.text("""
                INSERT INTO animal_species (id, name, name_ru, scientific_name, category, icon, is_active)
                VALUES (:id, :name, :name_ru, :scientific_name, :category, :icon, true)
                ON CONFLICT (name) DO NOTHING
            """),
            {
                "id": sid,
                "name": name,
                "name_ru": name_ru,
                "scientific_name": sci,
                "category": category,
                "icon": icon,
            }
        )

    # Seed some veterinary_dosing records for common drugs
    # We reference drugs by name ilike — look them up first
    # amoxicillin
    _insert_dosing(conn, "amoxicillin", _UUIDS["dog_id"],
                   route="oral", dose="10-20 mg/kg", frequency="q12h", max_dose="40 mg/kg/day",
                   notes="Give with food", source="Plumb's Veterinary Drug Handbook 9th ed.")
    _insert_dosing(conn, "amoxicillin", _UUIDS["cat_id"],
                   route="oral", dose="10 mg/kg", frequency="q12h", max_dose="20 mg/kg/day",
                   notes="Give with food", source="Plumb's Veterinary Drug Handbook 9th ed.")
    _insert_dosing(conn, "amoxicillin", _UUIDS["horse_id"],
                   route="oral", dose="10-30 mg/kg", frequency="q8-12h", max_dose=None,
                   notes="Limited oral bioavailability in horses", source="Plumb's Veterinary Drug Handbook")
    _insert_dosing(conn, "amoxicillin", _UUIDS["rabbit_id"],
                   route="oral", dose=None, frequency=None, max_dose=None,
                   is_toxic=True,
                   toxicity_note="CONTRAINDICATED in rabbits — disrupts GI flora, causes fatal enterotoxaemia",
                   source="Exotic Animal Formulary")

    # aspirin
    _insert_dosing(conn, "aspirin", _UUIDS["dog_id"],
                   route="oral", dose="10-25 mg/kg", frequency="q12h", max_dose="35 mg/kg/day",
                   notes="Anti-inflammatory dose; use with food", source="Plumb's")
    _insert_dosing(conn, "aspirin", _UUIDS["cat_id"],
                   route="oral", dose="10 mg/kg", frequency="q72h",
                   max_dose="10 mg/kg per dose",
                   is_toxic=True,
                   toxicity_note="Cats metabolise aspirin slowly — MUST dose q72h maximum; toxic accumulation is rapid",
                   source="Plumb's Veterinary Drug Handbook")

    # metronidazole
    _insert_dosing(conn, "metronidazole", _UUIDS["dog_id"],
                   route="oral", dose="10-15 mg/kg", frequency="q12h", max_dose="25 mg/kg/day",
                   notes="Anaerobic infections, GI disease; avoid prolonged use", source="Plumb's")
    _insert_dosing(conn, "metronidazole", _UUIDS["cat_id"],
                   route="oral", dose="10 mg/kg", frequency="q24h", max_dose="25 mg/kg/day",
                   notes="Very bitter taste — use coated tablets", source="Plumb's")

    # prednisolone
    _insert_dosing(conn, "prednisolone", _UUIDS["dog_id"],
                   route="oral", dose="0.5-1 mg/kg", frequency="q24h", max_dose="2 mg/kg/day",
                   notes="Anti-inflammatory dose; taper gradually", source="Plumb's")
    _insert_dosing(conn, "prednisolone", _UUIDS["cat_id"],
                   route="oral", dose="1-2 mg/kg", frequency="q24h", max_dose="4 mg/kg/day",
                   notes="Cats require higher doses than dogs; cats handle corticosteroids better", source="Plumb's")

    # enrofloxacin
    _insert_dosing(conn, "enrofloxacin", _UUIDS["dog_id"],
                   route="oral", dose="5-10 mg/kg", frequency="q24h", max_dose="20 mg/kg/day",
                   notes="Avoid in puppies < 12 months (cartilage toxicity)", source="Plumb's")
    _insert_dosing(conn, "enrofloxacin", _UUIDS["cat_id"],
                   route="oral", dose="5 mg/kg", frequency="q24h", max_dose="5 mg/kg/day",
                   is_toxic=True,
                   toxicity_note="HIGH DOSE CAUTION: >5 mg/kg can cause retinal degeneration and blindness in cats",
                   source="Plumb's Veterinary Drug Handbook")


def _insert_dosing(conn, drug_name, species_id, route, dose, frequency, max_dose=None,
                   is_toxic=False, toxicity_note=None, notes=None, source=None):
    """Look up drug by name and insert dosing — idempotent via ON CONFLICT DO UPDATE."""
    drug_row = conn.execute(
        sa.text("SELECT id FROM drugs WHERE lower(name) LIKE :name OR lower(generic_name) LIKE :name LIMIT 1"),
        {"name": f"%{drug_name.lower()}%"}
    ).fetchone()
    if not drug_row:
        return  # drug not yet in DB — skip silently

    drug_id = str(drug_row[0])
    entry_id = str(uuid.uuid4())
    conn.execute(
        sa.text("""
            INSERT INTO veterinary_dosing
              (id, drug_id, species_id, route, dose, frequency, max_dose,
               is_toxic, toxicity_note, notes, source, is_approved)
            VALUES
              (:id, :drug_id, :species_id, :route, :dose, :frequency, :max_dose,
               :is_toxic, :toxicity_note, :notes, :source, true)
            ON CONFLICT (drug_id, species_id, route) DO UPDATE SET
              dose = EXCLUDED.dose,
              frequency = EXCLUDED.frequency,
              max_dose = EXCLUDED.max_dose,
              is_toxic = EXCLUDED.is_toxic,
              toxicity_note = EXCLUDED.toxicity_note,
              notes = EXCLUDED.notes,
              source = EXCLUDED.source
        """),
        {
            "id": entry_id,
            "drug_id": drug_id,
            "species_id": species_id,
            "route": route or "oral",
            "dose": dose,
            "frequency": frequency,
            "max_dose": max_dose,
            "is_toxic": is_toxic,
            "toxicity_note": toxicity_note,
            "notes": notes,
            "source": source,
        }
    )


def downgrade():
    conn = op.get_bind()
    for sid in _UUIDS.values():
        conn.execute(
            sa.text("DELETE FROM animal_species WHERE id = :id"),
            {"id": sid}
        )
