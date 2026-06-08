"""colis pricing — prix calculé + modalité de paiement

Revision ID: 004
Revises: 003
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nouveau type enum pour la modalité de paiement
    op.execute(
        "CREATE TYPE colismodalitepaiement AS ENUM "
        "('A_LA_CONFIRMATION', 'A_LA_LIVRAISON')"
    )

    # Colonne modalite_paiement avec valeur par défaut
    op.add_column(
        "colis",
        sa.Column(
            "modalite_paiement",
            postgresql.ENUM(
                "A_LA_CONFIRMATION",
                "A_LA_LIVRAISON",
                name="colismodalitepaiement",
                create_type=False,
            ),
            nullable=False,
            server_default="A_LA_LIVRAISON",
        ),
    )

    # Le champ prix existait déjà en nullable — on le laisse tel quel.
    # Il sera désormais systématiquement renseigné à la création via le service
    # de tarification. Les anciens enregistrements sans prix restent NULL.


def downgrade() -> None:
    op.drop_column("colis", "modalite_paiement")
    op.execute("DROP TYPE IF EXISTS colismodalitepaiement")