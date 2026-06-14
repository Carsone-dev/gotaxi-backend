"""Crée la table demandes_inscription_chauffeur

Revision ID: 009
Revises: 008
Create Date: 2026-06-12

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False → SQLAlchemy ne tente pas de créer l'enum lors du create_table
# On gère la création manuellement avec checkfirst=True
demande_statut_enum = PgEnum(
    "NOUVELLE", "EN_COURS", "TRAITEE", "REJETEE",
    name="demandestatut",
    create_type=False,
)

demande_statut_enum_creator = PgEnum(
    "NOUVELLE", "EN_COURS", "TRAITEE", "REJETEE",
    name="demandestatut",
)


def upgrade() -> None:
    demande_statut_enum_creator.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "demandes_inscription_chauffeur",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("prenom", sa.String(100), nullable=False),
        sa.Column("nom", sa.String(100), nullable=False),
        sa.Column("telephone", sa.String(20), nullable=False),
        sa.Column("ville", sa.String(100), nullable=False),
        sa.Column("vehicule", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("statut", demande_statut_enum, nullable=False, server_default="NOUVELLE"),
        sa.Column("traite_par_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("traite_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("motif_rejet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_demandes_inscription_chauffeur"),
    )
    op.create_index("ix_demandes_inscription_chauffeur_telephone", "demandes_inscription_chauffeur", ["telephone"])


def downgrade() -> None:
    op.drop_index("ix_demandes_inscription_chauffeur_telephone", "demandes_inscription_chauffeur")
    op.drop_table("demandes_inscription_chauffeur")
    demande_statut_enum_creator.drop(op.get_bind(), checkfirst=True)
