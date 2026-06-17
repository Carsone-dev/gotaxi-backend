"""users: ajout champ genre (HOMME/FEMME/NON_DEFINI)

Revision ID: 017
Revises: 016
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None

genre_enum = sa.Enum("HOMME", "FEMME", "NON_DEFINI", name="genreuser")


def upgrade() -> None:
    genre_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column(
            "genre",
            genre_enum,
            nullable=False,
            server_default="NON_DEFINI",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "genre")
    genre_enum.drop(op.get_bind(), checkfirst=True)
