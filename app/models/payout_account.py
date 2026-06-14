from uuid import UUID
from sqlalchemy import String, Boolean, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.transaction import TransactionOperateur


class ComptePayoutChauffeur(Base, UUIDMixin, TimestampMixin):
    """Compte de réception des paiements d'un chauffeur.

    Contraintes :
    - Un chauffeur possède au plus UN compte actif (unique sur chauffeur_id).
    - Un numéro de téléphone appartient à UN seul chauffeur (unique sur telephone).
    """
    __tablename__ = "comptes_payout_chauffeurs"

    chauffeur_id: Mapped[UUID] = mapped_column(
        ForeignKey("chauffeurs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    operateur: Mapped[TransactionOperateur] = mapped_column(
        Enum(TransactionOperateur, name="transactionoperateur"), nullable=False
    )
    telephone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    chauffeur = relationship("Chauffeur", back_populates="compte_payout")
