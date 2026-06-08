from datetime import date
from uuid import UUID
from sqlalchemy import String, Boolean, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Chauffeur(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chauffeurs"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    cin_numero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    permis_numero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    permis_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    permis_expiration: Mapped[date | None] = mapped_column(Date, nullable=True)
    casier_judiciaire_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kyc_valide: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_valide_le: Mapped[date | None] = mapped_column(Date, nullable=True)
    autorisation_transfrontaliere: Mapped[bool] = mapped_column(Boolean, default=False)
    en_ligne: Mapped[bool] = mapped_column(Boolean, default=False)
    derniere_position_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    derniere_position_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    derniere_activite: Mapped[date | None] = mapped_column(Date, nullable=True)
    nombre_trajets: Mapped[int] = mapped_column(default=0)
    revenus_total: Mapped[int] = mapped_column(default=0)

    user = relationship("User", back_populates="chauffeur")
    vehicules = relationship("Vehicule", back_populates="chauffeur")
    voyages = relationship("Voyage", back_populates="chauffeur")