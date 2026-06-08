"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telephone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("nom", sa.String(100), nullable=False),
        sa.Column("prenom", sa.String(100), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("CLIENT", "CHAUFFEUR", "ADMIN", "SUPER_ADMIN", name="userrole"), nullable=False),
        sa.Column("statut", sa.Enum("ACTIF", "SUSPENDU", "EN_ATTENTE_KYC", "SUPPRIME", name="userstatus"), nullable=False),
        sa.Column("telephone_verifie", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("email_verifie", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("note_moyenne", sa.Numeric(3, 2), nullable=False, server_default="0"),
        sa.Column("nombre_avis", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fcm_token", sa.String(500), nullable=True),
        sa.Column("langue", sa.String(5), nullable=False, server_default="fr"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telephone", name="uq_users_telephone"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_telephone", "users", ["telephone"])

    op.create_table(
        "chauffeurs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cin_numero", sa.String(50), nullable=False),
        sa.Column("cin_url", sa.String(500), nullable=False),
        sa.Column("permis_numero", sa.String(50), nullable=False),
        sa.Column("permis_url", sa.String(500), nullable=False),
        sa.Column("permis_expiration", sa.Date(), nullable=False),
        sa.Column("casier_judiciaire_url", sa.String(500), nullable=True),
        sa.Column("kyc_valide", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("kyc_valide_le", sa.Date(), nullable=True),
        sa.Column("autorisation_transfrontaliere", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("en_ligne", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("derniere_position_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("derniere_position_lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("derniere_activite", sa.Date(), nullable=True),
        sa.Column("nombre_trajets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revenus_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chauffeurs_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_chauffeurs"),
        sa.UniqueConstraint("user_id", name="uq_chauffeurs_user_id"),
    )

    op.create_table(
        "vehicules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chauffeur_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("marque", sa.String(100), nullable=False),
        sa.Column("modele", sa.String(100), nullable=False),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("immatriculation", sa.String(20), nullable=False),
        sa.Column("couleur", sa.String(50), nullable=False),
        sa.Column("type_vehicule", sa.Enum("BERLINE", "SUV", "MINIBUS", "BUS", "MOTO", name="typevehicule"), nullable=False),
        sa.Column("nombre_places", sa.Integer(), nullable=False),
        sa.Column("climatise", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chauffeur_id"], ["chauffeurs.id"], name="fk_vehicules_chauffeur_id_chauffeurs"),
        sa.PrimaryKeyConstraint("id", name="pk_vehicules"),
        sa.UniqueConstraint("immatriculation", name="uq_vehicules_immatriculation"),
    )

    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("solde", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("devise", sa.String(3), nullable=False, server_default="XOF"),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_wallets_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_wallets"),
        sa.UniqueConstraint("user_id", name="uq_wallets_user_id"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Enum("RECHARGE", "PAIEMENT_VOYAGE", "PAIEMENT_COLIS", "REVERSEMENT", "REMBOURSEMENT", "COMMISSION", name="transactiontype"), nullable=False),
        sa.Column("statut", sa.Enum("EN_ATTENTE", "EN_COURS", "REUSSI", "ECHEC", "ANNULE", name="transactionstatut"), nullable=False),
        sa.Column("operateur", sa.Enum("MTN_MOMO", "MOOV_MONEY", "ORANGE_MONEY", "WALLET", name="transactionoperateur"), nullable=False),
        sa.Column("montant", sa.Integer(), nullable=False),
        sa.Column("reference_externe", sa.String(255), nullable=True),
        sa.Column("metadata_json", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], name="fk_transactions_wallet_id_wallets"),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
    )

    op.create_table(
        "voyages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chauffeur_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ville_depart", sa.String(100), nullable=False),
        sa.Column("ville_arrivee", sa.String(100), nullable=False),
        sa.Column("point_depart", sa.String(255), nullable=False),
        sa.Column("point_arrivee", sa.String(255), nullable=False),
        sa.Column("lat_depart", sa.Float(), nullable=False),
        sa.Column("lng_depart", sa.Float(), nullable=False),
        sa.Column("lat_arrivee", sa.Float(), nullable=False),
        sa.Column("lng_arrivee", sa.Float(), nullable=False),
        sa.Column("date_depart", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date_arrivee_estimee", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prix_par_place", sa.Integer(), nullable=False),
        sa.Column("nombre_places_total", sa.Integer(), nullable=False),
        sa.Column("nombre_places_restantes", sa.Integer(), nullable=False),
        sa.Column("accepte_colis", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("climatise", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("non_fumeur", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("statut", sa.Enum("PUBLIE", "COMPLET", "EN_COURS", "TERMINE", "ANNULE", name="voyagestatut"), nullable=False),
        sa.Column("distance_km", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chauffeur_id"], ["chauffeurs.id"], name="fk_voyages_chauffeur_id_chauffeurs"),
        sa.ForeignKeyConstraint(["vehicule_id"], ["vehicules.id"], name="fk_voyages_vehicule_id_vehicules"),
        sa.PrimaryKeyConstraint("id", name="pk_voyages"),
    )
    op.create_index("ix_voyages_date_depart", "voyages", ["date_depart"])

    op.create_table(
        "reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voyage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre_places", sa.Integer(), nullable=False),
        sa.Column("prix_total", sa.Integer(), nullable=False),
        sa.Column("statut", sa.Enum("EN_ATTENTE", "CONFIRMEE", "REFUSEE", "ANNULEE", "TERMINEE", name="reservationstatut"), nullable=False),
        sa.Column("code_confirmation", sa.String(6), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["voyage_id"], ["voyages.id"], name="fk_reservations_voyage_id_voyages"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], name="fk_reservations_client_id_users"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], name="fk_reservations_transaction_id_transactions"),
        sa.PrimaryKeyConstraint("id", name="pk_reservations"),
    )

    op.create_table(
        "colis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(30), nullable=False),
        sa.Column("expediteur_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voyage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chauffeur_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type_colis", sa.Enum("DOCUMENT", "PETIT", "MOYEN", "GRAND", name="colistype"), nullable=False),
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
        sa.Column("statut", sa.Enum("EN_ATTENTE", "VALIDE", "ASSIGNE", "RECUPERE", "EN_ROUTE", "LIVRE", "ANNULE", "LITIGE", name="colisstatut"), nullable=False),
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

    op.create_table(
        "suivi_colis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("colis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("statut", sa.Enum("EN_ATTENTE", "VALIDE", "ASSIGNE", "RECUPERE", "EN_ROUTE", "LIVRE", "ANNULE", "LITIGE", name="colisstatut"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("ville", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["colis_id"], ["colis.id"], name="fk_suivi_colis_colis_id_colis"),
        sa.PrimaryKeyConstraint("id", name="pk_suivi_colis"),
    )

    op.create_table(
        "avis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auteur_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cible_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voyage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Integer(), nullable=False),
        sa.Column("commentaire", sa.String(1000), nullable=True),
        sa.Column("tags", postgresql.JSON(), nullable=True),
        sa.Column("signale", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["auteur_id"], ["users.id"], name="fk_avis_auteur_id_users"),
        sa.ForeignKeyConstraint(["cible_id"], ["users.id"], name="fk_avis_cible_id_users"),
        sa.ForeignKeyConstraint(["voyage_id"], ["voyages.id"], name="fk_avis_voyage_id_voyages"),
        sa.PrimaryKeyConstraint("id", name="pk_avis"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Enum("RESERVATION", "VOYAGE", "COLIS", "PAIEMENT", "SYSTEME", name="notiftype"), nullable=False),
        sa.Column("titre", sa.String(255), nullable=False),
        sa.Column("corps", sa.String(1000), nullable=False),
        sa.Column("lue", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("data", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_notifications_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entite", sa.String(100), nullable=False),
        sa.Column("entite_id", sa.String(50), nullable=True),
        sa.Column("details", postgresql.JSON(), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], name="fk_audit_logs_admin_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("avis")
    op.drop_table("suivi_colis")
    op.drop_table("colis")
    op.drop_table("reservations")
    op.drop_index("ix_voyages_date_depart", "voyages")
    op.drop_table("voyages")
    op.drop_table("transactions")
    op.drop_table("wallets")
    op.drop_table("vehicules")
    op.drop_table("chauffeurs")
    op.drop_index("ix_users_telephone", "users")
    op.drop_table("users")