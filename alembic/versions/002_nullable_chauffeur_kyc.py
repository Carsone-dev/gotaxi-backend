"""nullable chauffeur kyc fields

Revision ID: 002
Revises: 001
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("chauffeurs", "cin_numero", nullable=True)
    op.alter_column("chauffeurs", "cin_url", nullable=True)
    op.alter_column("chauffeurs", "permis_numero", nullable=True)
    op.alter_column("chauffeurs", "permis_url", nullable=True)
    op.alter_column("chauffeurs", "permis_expiration", nullable=True)


def downgrade() -> None:
    op.execute("UPDATE chauffeurs SET cin_numero = '' WHERE cin_numero IS NULL")
    op.execute("UPDATE chauffeurs SET cin_url = '' WHERE cin_url IS NULL")
    op.execute("UPDATE chauffeurs SET permis_numero = '' WHERE permis_numero IS NULL")
    op.execute("UPDATE chauffeurs SET permis_url = '' WHERE permis_url IS NULL")
    op.execute("UPDATE chauffeurs SET permis_expiration = CURRENT_DATE WHERE permis_expiration IS NULL")
    op.alter_column("chauffeurs", "cin_numero", nullable=False)
    op.alter_column("chauffeurs", "cin_url", nullable=False)
    op.alter_column("chauffeurs", "permis_numero", nullable=False)
    op.alter_column("chauffeurs", "permis_url", nullable=False)
    op.alter_column("chauffeurs", "permis_expiration", nullable=False)