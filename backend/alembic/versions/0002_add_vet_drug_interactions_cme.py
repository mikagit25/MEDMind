"""Add drug_interactions, animal_species, veterinary_dosing, cme_credits tables

Revision ID: 0002
Revises: 0001_initial_schema
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0002"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # drug_interactions
    op.create_table(
        "drug_interactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("drug_a_id", UUID(as_uuid=True), sa.ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drug_b_id", UUID(as_uuid=True), sa.ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(20), server_default="moderate"),
        sa.Column("mechanism", sa.Text),
        sa.Column("clinical_effect", sa.Text),
        sa.Column("management", sa.Text),
        sa.Column("evidence_level", sa.String(10), server_default="C"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.UniqueConstraint("drug_a_id", "drug_b_id", name="uq_drug_interaction_pair"),
    )
    op.create_index("ix_drug_interactions_drug_a", "drug_interactions", ["drug_a_id"])
    op.create_index("ix_drug_interactions_drug_b", "drug_interactions", ["drug_b_id"])

    # animal_species
    op.create_table(
        "animal_species",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("name_ru", sa.String(100)),
        sa.Column("scientific_name", sa.String(200)),
        sa.Column("category", sa.String(50)),
        sa.Column("icon", sa.String(10)),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )

    # Seed basic species
    op.execute("""
        INSERT INTO animal_species (id, name, name_ru, scientific_name, category, icon) VALUES
        (gen_random_uuid(), 'Dog',    'Собака',  'Canis lupus familiaris', 'companion', '🐕'),
        (gen_random_uuid(), 'Cat',    'Кошка',   'Felis catus',            'companion', '🐈'),
        (gen_random_uuid(), 'Horse',  'Лошадь',  'Equus caballus',         'livestock', '🐎'),
        (gen_random_uuid(), 'Rabbit', 'Кролик',  'Oryctolagus cuniculus',  'companion', '🐇'),
        (gen_random_uuid(), 'Cattle', 'КРС',     'Bos taurus',             'livestock', '🐄'),
        (gen_random_uuid(), 'Bird',   'Птица',   'Aves',                   'avian',     '🦜')
        ON CONFLICT (name) DO NOTHING
    """)

    # veterinary_dosing
    op.create_table(
        "veterinary_dosing",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("drug_id", UUID(as_uuid=True), sa.ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("species_id", UUID(as_uuid=True), sa.ForeignKey("animal_species.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dose", sa.String(200)),
        sa.Column("route", sa.String(50)),
        sa.Column("frequency", sa.String(100)),
        sa.Column("max_dose", sa.String(100)),
        sa.Column("is_toxic", sa.Boolean, server_default="false"),
        sa.Column("toxicity_note", sa.Text),
        sa.Column("is_approved", sa.Boolean, server_default="true"),
        sa.Column("notes", sa.Text),
        sa.Column("source", sa.String(200)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.UniqueConstraint("drug_id", "species_id", "route", name="uq_vet_dosing"),
    )
    op.create_index("ix_vet_dosing_drug", "veterinary_dosing", ["drug_id"])
    op.create_index("ix_vet_dosing_species", "veterinary_dosing", ["species_id"])

    # cme_credits
    op.create_table(
        "cme_credits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_id", UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=True),
        sa.Column("credit_type", sa.String(50), server_default="AMA_PRA_1"),
        sa.Column("credits_earned", sa.Numeric(4, 1), server_default="1.0"),
        sa.Column("activity_title", sa.String(300)),
        sa.Column("completion_date", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("certificate_url", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )
    op.create_index("ix_cme_credits_user", "cme_credits", ["user_id"])


def downgrade() -> None:
    op.drop_table("cme_credits")
    op.drop_table("veterinary_dosing")
    op.drop_table("animal_species")
    op.drop_table("drug_interactions")
