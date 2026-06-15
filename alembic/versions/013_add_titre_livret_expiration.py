"""add titre and livret_bord expiration dates

Revision ID: 013
Revises: 012
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vehicules", sa.Column("titre_expiration", sa.Date(), nullable=True))
    op.add_column("vehicules", sa.Column("livret_bord_expiration", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("vehicules", "livret_bord_expiration")
    op.drop_column("vehicules", "titre_expiration")
