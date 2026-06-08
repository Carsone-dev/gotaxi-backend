import enum
from uuid import UUID
from sqlalchemy import String, Boolean, Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class TypeVehicule(str, enum.Enum):
    BERLINE = "BERLINE"
    SUV = "SUV"
    MINIBUS = "MINIBUS"
    BUS = "BUS"
    MOTO = "MOTO"


class Vehicule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vehicules"

    chauffeur_id: Mapped[UUID] = mapped_column(ForeignKey("chauffeurs.id"))
    marque: Mapped[str] = mapped_column(String(100))
    modele: Mapped[str] = mapped_column(String(100))
    annee: Mapped[int] = mapped_column(Integer)
    immatriculation: Mapped[str] = mapped_column(String(20), unique=True)
    couleur: Mapped[str] = mapped_column(String(50))
    type_vehicule: Mapped[TypeVehicule] = mapped_column(Enum(TypeVehicule))
    nombre_places: Mapped[int] = mapped_column(Integer)
    climatise: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    chauffeur = relationship("Chauffeur", back_populates="vehicules")