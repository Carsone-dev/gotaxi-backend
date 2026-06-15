import enum
from uuid import UUID
from sqlalchemy import String, Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class TransactionType(str, enum.Enum):
    # Nouveaux types — frais de mise en relation plateforme
    FRAIS_RESERVATION = "FRAIS_RESERVATION"  # 200 FCFA × nb_places
    FRAIS_COLIS = "FRAIS_COLIS"              # 100 FCFA par demande colis
    # Anciens types conservés pour l'historique
    RECHARGE = "RECHARGE"
    PAIEMENT_VOYAGE = "PAIEMENT_VOYAGE"
    PAIEMENT_COLIS = "PAIEMENT_COLIS"
    REVERSEMENT = "REVERSEMENT"
    REMBOURSEMENT = "REMBOURSEMENT"
    COMMISSION = "COMMISSION"


class TransactionStatut(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    EN_COURS = "EN_COURS"
    REUSSI = "REUSSI"
    ECHEC = "ECHEC"
    ANNULE = "ANNULE"


class TransactionOperateur(str, enum.Enum):
    MTN_MOMO = "MTN_MOMO"
    MOOV_MONEY = "MOOV_MONEY"
    ORANGE_MONEY = "ORANGE_MONEY"
    CELTIS = "CELTIS"
    FEDAPAY = "FEDAPAY"
    WALLET = "WALLET"


class Transaction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transactions"

    # wallet_id conservé nullable pour l'historique des anciennes transactions
    wallet_id: Mapped[UUID | None] = mapped_column(ForeignKey("wallets.id"), nullable=True)
    # Utilisateur ayant payé les frais (nouveau modèle)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Liens vers les entités concernées
    reservation_id: Mapped[UUID | None] = mapped_column(ForeignKey("reservations.id"), nullable=True)
    colis_id: Mapped[UUID | None] = mapped_column(ForeignKey("colis.id"), nullable=True)

    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    statut: Mapped[TransactionStatut] = mapped_column(
        Enum(TransactionStatut), default=TransactionStatut.EN_ATTENTE
    )
    operateur: Mapped[TransactionOperateur] = mapped_column(Enum(TransactionOperateur))
    montant: Mapped[int] = mapped_column(Integer)
    reference_externe: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    wallet = relationship("Wallet", back_populates="transactions")
