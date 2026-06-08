"""colis mobile refactor — align with mobile spec

Revision ID: 003
Revises: 002
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop tables that reference old enum types (dependency order)
    op.drop_table("suivi_colis")
    op.drop_table("colis")

    # 2. Drop old enum types
    op.execute("DROP TYPE IF EXISTS colisstatut")
    op.execute("DROP TYPE IF EXISTS colistype")

    # 3. Create new enum types
    op.execute(
        "CREATE TYPE coliscategorie AS ENUM "
        "('DOCUMENTS', 'VETEMENTS', 'ELECTRONIQUE', 'ALIMENTAIRE', 'FRAGILE', 'AUTRE')"
    )
    op.execute(
        "CREATE TYPE colisstatut AS ENUM "
        "('EN_ATTENTE', 'CONFIRME', 'EN_TRANSIT', 'LIVRE', 'ANNULE')"
    )

    # 4. Recreate colis table aligned with mobile spec
    op.create_table(
        "colis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voyage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expediteur_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ville_depart", sa.String(100), nullable=False),
        sa.Column("ville_arrivee", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column(
            "categorie",
            postgresql.ENUM(
                "DOCUMENTS", "VETEMENTS", "ELECTRONIQUE", "ALIMENTAIRE", "FRAGILE", "AUTRE",
                name="coliscategorie",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("poids_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("fragile", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("destinataire_nom", sa.String(100), nullable=False),
        sa.Column("destinataire_telephone", sa.String(20), nullable=False),
        sa.Column("prix", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "statut",
            postgresql.ENUM(
                "EN_ATTENTE", "CONFIRME", "EN_TRANSIT", "LIVRE", "ANNULE",
                name="colisstatut",
                create_type=False,
            ),
            nullable=False,
            server_default="EN_ATTENTE",
        ),
        sa.Column("code_suivi", sa.String(20), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["voyage_id"], ["voyages.id"], name="fk_colis_voyage_id_voyages"),
        sa.ForeignKeyConstraint(["expediteur_id"], ["users.id"], name="fk_colis_expediteur_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_colis"),
        sa.UniqueConstraint("code_suivi", name="uq_colis_code_suivi"),
    )
    op.create_index("ix_colis_code_suivi", "colis", ["code_suivi"])

    # 5. Recreate suivi_colis with new colisstatut
    op.create_table(
        "suivi_colis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("colis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "statut",
            postgresql.ENUM(
                "EN_ATTENTE", "CONFIRME", "EN_TRANSIT", "LIVRE", "ANNULE",
                name="colisstatut",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("ville", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["colis_id"], ["colis.id"], name="fk_suivi_colis_colis_id_colis"),
        sa.PrimaryKeyConstraint("id", name="pk_suivi_colis"),
    )


def downgrade() -> None:
    op.drop_table("suivi_colis")
    op.drop_table("colis")

    op.execute("DROP TYPE IF EXISTS coliscategorie")
    op.execute("DROP TYPE IF EXISTS colisstatut")

    # Restore old enum types
    op.execute(
        "CREATE TYPE colisstatut AS ENUM "
        "('EN_ATTENTE', 'VALIDE', 'ASSIGNE', 'RECUPERE', 'EN_ROUTE', 'LIVRE', 'ANNULE', 'LITIGE')"
    )
    op.execute(
        "CREATE TYPE colistype AS ENUM ('DOCUMENT', 'PETIT', 'MOYEN', 'GRAND')"
    )

    # Restore old colis table
    op.create_table(
        "colis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(30), nullable=False),
        sa.Column("expediteur_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voyage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chauffeur_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "type_colis",
            postgresql.ENUM("DOCUMENT", "PETIT", "MOYEN", "GRAND", name="colistype", create_type=False),
            nullable=False,
        ),
        sa.Column("poids_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("ville_depart", sa.String(100), nullable=False),
        sa.Column("ville_arrivee", sa.String(100), nullable=False),
        sa.Column("adresse_depart", sa.String(500), nullable=False),
        sa.Column("adresse_arrivee", sa.String(500), nullable=False),
        sa.Column("destinataire_nom", sa.String(100), nullable=False),
        sa.Column("destinataire_telephone", sa.String(20), nullable=False),
        sa.Column("code_retrait", sa.String(8), nullable=False),
        sa.Column("prix", sa.Integer(), nullable=False),
        sa.Column(
            "statut",
            postgresql.ENUM(
                "EN_ATTENTE", "VALIDE", "ASSIGNE", "RECUPERE", "EN_ROUTE", "LIVRE", "ANNULE", "LITIGE",
                name="colisstatut",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("date_retrait_prevu", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_livraison_prevue", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date_livraison_reelle", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["expediteur_id"], ["users.id"], name="fk_colis_expediteur_id_users"),
        sa.ForeignKeyConstraint(["voyage_id"], ["voyages.id"], name="fk_colis_voyage_id_voyages"),
        sa.ForeignKeyConstraint(["chauffeur_id"], ["chauffeurs.id"], name="fk_colis_chauffeur_id_chauffeurs"),
        sa.PrimaryKeyConstraint("id", name="pk_colis"),
        sa.UniqueConstraint("reference", name="uq_colis_reference"),
    )
    op.create_index("ix_colis_reference", "colis", ["reference"])

    # Restore old suivi_colis
    op.create_table(
        "suivi_colis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("colis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "statut",
            postgresql.ENUM(
                "EN_ATTENTE", "VALIDE", "ASSIGNE", "RECUPERE", "EN_ROUTE", "LIVRE", "ANNULE", "LITIGE",
                name="colisstatut",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("ville", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["colis_id"], ["colis.id"], name="fk_suivi_colis_colis_id_colis"),
        sa.PrimaryKeyConstraint("id", name="pk_suivi_colis"),
    )