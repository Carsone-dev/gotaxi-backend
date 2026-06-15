"""refactor: modèle économique — frais plateforme (200 FCFA/place réservation, 100 FCFA colis)

Supprime le wallet client/chauffeur du flux de paiement.
La plateforme ne collecte que ses frais de mise en relation via FedaPay Mobile Money.

Revision ID: 015
Revises: 014
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Nouvelles valeurs d'enum ──────────────────────────────────────────
    op.execute("ALTER TYPE reservationstatut ADD VALUE IF NOT EXISTS 'EN_ATTENTE_PAIEMENT' BEFORE 'EN_ATTENTE'")
    op.execute("ALTER TYPE colisstatut ADD VALUE IF NOT EXISTS 'EN_ATTENTE_PAIEMENT' BEFORE 'EN_ATTENTE'")
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'FRAIS_RESERVATION'")
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'FRAIS_COLIS'")

    # ── 2. Reservations ──────────────────────────────────────────────────────
    op.add_column("reservations", sa.Column("frais_plateforme", sa.Integer(), nullable=False, server_default="200"))
    op.add_column("reservations", sa.Column("fedapay_transaction_id", sa.String(100), nullable=True))
    op.add_column("reservations", sa.Column("paiement_expire_a", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("reservations", "modalite_paiement", nullable=True)
    op.alter_column("reservations", "transaction_id", nullable=True)

    # ── 3. Colis ─────────────────────────────────────────────────────────────
    op.add_column("colis", sa.Column("frais_plateforme", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("colis", sa.Column("fedapay_transaction_id", sa.String(100), nullable=True))
    op.add_column("colis", sa.Column("paiement_expire_a", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("colis", "modalite_paiement", nullable=True)

    # ── 4. Transactions : wallet_id nullable + FK vers user/reservation/colis ─
    op.alter_column("transactions", "wallet_id", nullable=True)
    op.add_column("transactions", sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True))
    op.add_column("transactions", sa.Column("reservation_id", sa.Uuid(as_uuid=True), nullable=True))
    op.add_column("transactions", sa.Column("colis_id", sa.Uuid(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_transactions_user_id_users", "transactions", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_transactions_reservation_id_reservations", "transactions", "reservations", ["reservation_id"], ["id"])
    op.create_foreign_key("fk_transactions_colis_id_colis", "transactions", "colis", ["colis_id"], ["id"])


def downgrade():
    op.drop_constraint("fk_transactions_colis_id_colis", "transactions", type_="foreignkey")
    op.drop_constraint("fk_transactions_reservation_id_reservations", "transactions", type_="foreignkey")
    op.drop_constraint("fk_transactions_user_id_users", "transactions", type_="foreignkey")
    op.drop_column("transactions", "colis_id")
    op.drop_column("transactions", "reservation_id")
    op.drop_column("transactions", "user_id")
    op.alter_column("transactions", "wallet_id", nullable=False)

    op.alter_column("colis", "modalite_paiement", nullable=False)
    op.drop_column("colis", "paiement_expire_a")
    op.drop_column("colis", "fedapay_transaction_id")
    op.drop_column("colis", "frais_plateforme")

    op.alter_column("reservations", "transaction_id", nullable=False)
    op.alter_column("reservations", "modalite_paiement", nullable=False)
    op.drop_column("reservations", "paiement_expire_a")
    op.drop_column("reservations", "fedapay_transaction_id")
    op.drop_column("reservations", "frais_plateforme")
