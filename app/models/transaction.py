import enum
from uuid import UUID
from sqlalchemy import String, Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class TransactionType(str, enum.Enum):
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
    WALLET = "WALLET"


class Transaction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transactions"

    wallet_id: Mapped[UUID] = mapped_column(ForeignKey("wallets.id"))
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    statut: Mapped[TransactionStatut] = mapped_column(
        Enum(TransactionStatut), default=TransactionStatut.EN_ATTENTE
    )
    operateur: Mapped[TransactionOperateur] = mapped_column(Enum(TransactionOperateur))
    montant: Mapped[int] = mapped_column(Integer)
    reference_externe: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    wallet = relationship("Wallet", back_populates="transactions")