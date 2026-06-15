import enum
from datetime import datetime
from uuid import UUID
from sqlalchemy import Integer, ForeignKey, Enum, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class ReservationStatut(str, enum.Enum):
    EN_ATTENTE_PAIEMENT = "EN_ATTENTE_PAIEMENT"  # frais plateforme non encore payés
    EN_ATTENTE = "EN_ATTENTE"                      # frais payés, chauffeur doit accepter
    CONFIRMEE = "CONFIRMEE"
    REFUSEE = "REFUSEE"
    ANNULEE = "ANNULEE"
    TERMINEE = "TERMINEE"


class ModalitePaiementReservation(str, enum.Enum):
    """Conservé pour compatibilité avec les anciennes lignes en base."""
    WALLET = "WALLET"
    ESPECES = "ESPECES"


class Reservation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reservations"

    voyage_id: Mapped[UUID] = mapped_column(ForeignKey("voyages.id"))
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    nombre_places: Mapped[int] = mapped_column(Integer)
    prix_total: Mapped[int] = mapped_column(Integer)
    statut: Mapped[ReservationStatut] = mapped_column(
        Enum(ReservationStatut), default=ReservationStatut.EN_ATTENTE_PAIEMENT
    )
    # Frais de mise en relation collectés par la plateforme (200 FCFA × nb_places)
    frais_plateforme: Mapped[int] = mapped_column(Integer, default=200)
    # Référence transaction FedaPay pour le paiement des frais
    fedapay_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Expiration du délai de paiement (15 min après création)
    paiement_expire_a: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    code_confirmation: Mapped[str] = mapped_column(String(6))
    # Conservé nullable pour compatibilité historique
    modalite_paiement: Mapped[ModalitePaiementReservation | None] = mapped_column(
        Enum(ModalitePaiementReservation), nullable=True
    )
    transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )

    voyage = relationship("Voyage", back_populates="reservations")
    client = relationship("User", back_populates="reservations")
