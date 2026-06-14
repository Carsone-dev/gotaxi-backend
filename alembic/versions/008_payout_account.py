"""Crée la table comptes_payout_chauffeurs

Revision ID: 008
Revises: 007
Create Date: 2026-06-11

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "comptes_payout_chauffeurs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chauffeur_id", sa.UUID(), nullable=False),
        sa.Column(
            "operateur",
            PgEnum(name="transactionoperateur", create_type=False),
            nullable=False,
        ),
        sa.Column("telephone", sa.String(20), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["chauffeur_id"], ["chauffeurs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chauffeur_id"),
        sa.UniqueConstraint("telephone"),
    )
    op.create_index("ix_comptes_payout_chauffeur_id", "comptes_payout_chauffeurs", ["chauffeur_id"])


def downgrade() -> None:
    op.drop_index("ix_comptes_payout_chauffeur_id", table_name="comptes_payout_chauffeurs")
    op.drop_table("comptes_payout_chauffeurs")
