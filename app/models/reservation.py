import enum
from uuid import UUID
from sqlalchemy import Integer, ForeignKey, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class ReservationStatut(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    CONFIRMEE = "CONFIRMEE"
    REFUSEE = "REFUSEE"
    ANNULEE = "ANNULEE"
    TERMINEE = "TERMINEE"


class Reservation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reservations"

    voyage_id: Mapped[UUID] = mapped_column(ForeignKey("voyages.id"))
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    nombre_places: Mapped[int] = mapped_column(Integer)
    prix_total: Mapped[int] = mapped_column(Integer)
    statut: Mapped[ReservationStatut] = mapped_column(
        Enum(ReservationStatut), default=ReservationStatut.EN_ATTENTE
    )
    code_confirmation: Mapped[str] = mapped_column(String(6))
    transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )

    voyage = relationship("Voyage", back_populates="reservations")
    client = relationship("User", back_populates="reservations")