"""Ajoute CELTIS dans l'enum transactionoperateur

Revision ID: 006
Revises: 005
Create Date: 2026-06-11

"""
from typing import Sequence, Union
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE doit être hors transaction sur PG < 12.
    # Sur PG 12+ c'est supporté dans une transaction, mais on reste prudent.
    op.execute("ALTER TYPE transactionoperateur ADD VALUE IF NOT EXISTS 'CELTIS'")


def downgrade() -> None:
    # PostgreSQL ne supporte pas la suppression d'une valeur d'enum.
    # La valeur CELTIS reste dans le type mais ne sera plus utilisée.
    pass
