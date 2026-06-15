"""remove livret_bord_expiration (livret de bord is a permanent document)

Revision ID: 014
Revises: 013
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("vehicules", "livret_bord_expiration")


def downgrade():
    op.add_column("vehicules", sa.Column("livret_bord_expiration", sa.Date(), nullable=True))
