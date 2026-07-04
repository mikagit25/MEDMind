"""fix_vet_dosing_columns

Add missing columns to veterinary_dosing and migrate data from old schema.

Revision ID: 0036_fix_vet_dosing_columns
Revises: 0035_enterprise_leads
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = '0036_fix_vet_dosing_columns'
down_revision = '0035_enterprise_leads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns (if they don't exist yet)
    conn = op.get_bind()
    existing = {row[0] for row in conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='veterinary_dosing'")
    )}

    if 'dose' not in existing:
        op.add_column('veterinary_dosing', sa.Column('dose', sa.String(200), nullable=True))
    if 'max_dose' not in existing:
        op.add_column('veterinary_dosing', sa.Column('max_dose', sa.String(100), nullable=True))
    if 'is_toxic' not in existing:
        op.add_column('veterinary_dosing', sa.Column('is_toxic', sa.Boolean(), nullable=True, server_default='false'))
    if 'toxicity_note' not in existing:
        op.add_column('veterinary_dosing', sa.Column('toxicity_note', sa.Text(), nullable=True))
    if 'is_approved' not in existing:
        op.add_column('veterinary_dosing', sa.Column('is_approved', sa.Boolean(), nullable=True, server_default='true'))
    if 'source' not in existing:
        op.add_column('veterinary_dosing', sa.Column('source', sa.String(200), nullable=True))

    # Migrate data from old columns to new ones
    if 'dose_mg_kg' in existing and 'dose' not in existing:
        # dose_mg_kg was already added above as 'dose'
        conn.execute(sa.text("UPDATE veterinary_dosing SET dose = dose_mg_kg WHERE dose IS NULL"))
    elif 'dose_mg_kg' in existing:
        conn.execute(sa.text("UPDATE veterinary_dosing SET dose = dose_mg_kg WHERE dose IS NULL"))

    if 'contraindicated' in existing and 'is_toxic' not in existing:
        conn.execute(sa.text("UPDATE veterinary_dosing SET is_toxic = contraindicated WHERE is_toxic IS NULL"))
    elif 'contraindicated' in existing:
        conn.execute(sa.text("UPDATE veterinary_dosing SET is_toxic = contraindicated WHERE is_toxic IS NULL"))

    # Drop old columns that are no longer in the model
    if 'dose_mg_kg' in existing:
        op.drop_column('veterinary_dosing', 'dose_mg_kg')
    if 'contraindicated' in existing:
        op.drop_column('veterinary_dosing', 'contraindicated')
    if 'drug_name' in existing:
        op.drop_column('veterinary_dosing', 'drug_name')

    # Add unique constraint if not present
    try:
        op.create_unique_constraint(
            'uq_vet_dosing_drug_species_route',
            'veterinary_dosing',
            ['drug_id', 'species_id', 'route']
        )
    except Exception:
        pass


def downgrade() -> None:
    op.add_column('veterinary_dosing', sa.Column('dose_mg_kg', sa.String(100), nullable=True))
    op.add_column('veterinary_dosing', sa.Column('contraindicated', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('veterinary_dosing', sa.Column('drug_name', sa.String(200), nullable=False, server_default=''))
    op.execute("UPDATE veterinary_dosing SET dose_mg_kg = dose, contraindicated = is_toxic")
    op.drop_column('veterinary_dosing', 'dose')
    op.drop_column('veterinary_dosing', 'max_dose')
    op.drop_column('veterinary_dosing', 'is_toxic')
    op.drop_column('veterinary_dosing', 'toxicity_note')
    op.drop_column('veterinary_dosing', 'is_approved')
    op.drop_column('veterinary_dosing', 'source')
