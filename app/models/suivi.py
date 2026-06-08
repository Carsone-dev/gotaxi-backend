from uuid import UUID
from sqlalchemy import String, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.colis import ColisStatut


class SuiviColis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "suivi_colis"

    colis_id: Mapped[UUID] = mapped_column(ForeignKey("colis.id"))
    statut: Mapped[ColisStatut] = mapped_column(Enum(ColisStatut))
    description: Mapped[str] = mapped_column(String(500))
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lng: Mapped[float | None] = mapped_column(nullable=True)
    ville: Mapped[str | None] = mapped_column(String(100), nullable=True)

    colis = relationship("Colis", back_populates="suivi")