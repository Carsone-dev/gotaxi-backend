"""add vehicule regulatory documents

Revision ID: 012
Revises: 011
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vehicules", sa.Column("assurance_url", sa.String(500), nullable=True))
    op.add_column("vehicules", sa.Column("assurance_expiration", sa.Date(), nullable=True))
    op.add_column("vehicules", sa.Column("visite_technique_url", sa.String(500), nullable=True))
    op.add_column("vehicules", sa.Column("visite_technique_expiration", sa.Date(), nullable=True))
    op.add_column("vehicules", sa.Column("titre_url", sa.String(500), nullable=True))
    op.add_column("vehicules", sa.Column("livret_bord_url", sa.String(500), nullable=True))
    op.add_column("vehicules", sa.Column("docs_vehicule_valides", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("vehicules", sa.Column("docs_vehicule_valides_le", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("vehicules", "docs_vehicule_valides_le")
    op.drop_column("vehicules", "docs_vehicule_valides")
    op.drop_column("vehicules", "livret_bord_url")
    op.drop_column("vehicules", "titre_url")
    op.drop_column("vehicules", "visite_technique_expiration")
    op.drop_column("vehicules", "visite_technique_url")
    op.drop_column("vehicules", "assurance_expiration")
    op.drop_column("vehicules", "assurance_url")
