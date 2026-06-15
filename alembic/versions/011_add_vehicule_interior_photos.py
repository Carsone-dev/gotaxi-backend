"""add vehicule interior photos

Revision ID: 011
Revises: 010
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "vehicules",
        sa.Column("photos_interieures", sa.JSON(), server_default="[]", nullable=False),
    )


def downgrade():
    op.drop_column("vehicules", "photos_interieures")
