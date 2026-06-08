import enum
from datetime import datetime
from uuid import UUID
from sqlalchemy import String, Integer, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class VoyageStatut(str, enum.Enum):
    PUBLIE = "PUBLIE"
    COMPLET = "COMPLET"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    ANNULE = "ANNULE"


class Voyage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "voyages"

    chauffeur_id: Mapped[UUID] = mapped_column(ForeignKey("chauffeurs.id"))
    vehicule_id: Mapped[UUID] = mapped_column(ForeignKey("vehicules.id"))
    ville_depart: Mapped[str] = mapped_column(String(100))
    ville_arrivee: Mapped[str] = mapped_column(String(100))
    point_depart: Mapped[str] = mapped_column(String(255))
    point_arrivee: Mapped[str] = mapped_column(String(255))
    lat_depart: Mapped[float] = mapped_column()
    lng_depart: Mapped[float] = mapped_column()
    lat_arrivee: Mapped[float] = mapped_column()
    lng_arrivee: Mapped[float] = mapped_column()
    date_depart: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    date_arrivee_estimee: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    prix_par_place: Mapped[int] = mapped_column(Integer)
    nombre_places_total: Mapped[int] = mapped_column(Integer)
    nombre_places_restantes: Mapped[int] = mapped_column(Integer)
    accepte_colis: Mapped[bool] = mapped_column(Boolean, default=True)
    climatise: Mapped[bool] = mapped_column(Boolean, default=False)
    non_fumeur: Mapped[bool] = mapped_column(Boolean, default=True)
    statut: Mapped[VoyageStatut] = mapped_column(Enum(VoyageStatut), default=VoyageStatut.PUBLIE)
    distance_km: Mapped[int | None] = mapped_column(nullable=True)

    chauffeur = relationship("Chauffeur", back_populates="voyages")
    vehicule = relationship("Vehicule")
    reservations = relationship("Reservation", back_populates="voyage")
    colis = relationship("Colis", back_populates="voyage")