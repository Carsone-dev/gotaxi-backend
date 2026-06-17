"""avis: contrainte unique (auteur, voyage) + index cible_id et auteur_id

Un client ne peut laisser qu'un seul avis par voyage (enforced DB-level).
Index sur cible_id pour les requêtes de listing par chauffeur.
Index sur auteur_id pour le check anti-doublon à la soumission.

Revision ID: 016
Revises: 015
Create Date: 2026-06-17
"""
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Index sur cible_id : requêtes GET /avis/chauffeur/{id} et stats admin
    op.create_index("ix_avis_cible_id", "avis", ["cible_id"])

    # Index sur auteur_id : check anti-doublon (auteur + voyage_id)
    op.create_index("ix_avis_auteur_id", "avis", ["auteur_id"])

    # Contrainte unique partielle : un auteur ne peut noter qu'une fois par voyage.
    # Partielle (WHERE voyage_id IS NOT NULL) car voyage_id est nullable en base
    # (lignes historiques sans voyage_id restent valides).
    op.create_index(
        "uq_avis_auteur_voyage",
        "avis",
        ["auteur_id", "voyage_id"],
        unique=True,
        postgresql_where="voyage_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_avis_auteur_voyage", table_name="avis")
    op.drop_index("ix_avis_auteur_id", table_name="avis")
    op.drop_index("ix_avis_cible_id", table_name="avis")
