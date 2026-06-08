import enum
from uuid import UUID
from sqlalchemy import String, Numeric, ForeignKey, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class ColisCategorie(str, enum.Enum):
    DOCUMENTS = "DOCUMENTS"
    VETEMENTS = "VETEMENTS"
    ELECTRONIQUE = "ELECTRONIQUE"
    ALIMENTAIRE = "ALIMENTAIRE"
    FRAGILE = "FRAGILE"
    AUTRE = "AUTRE"


class ColisStatut(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    CONFIRME = "CONFIRME"
    EN_TRANSIT = "EN_TRANSIT"
    LIVRE = "LIVRE"
    ANNULE = "ANNULE"


class ColisModalitePaiement(str, enum.Enum):
    A_LA_CONFIRMATION = "A_LA_CONFIRMATION"  # client paie quand le chauffeur accepte
    A_LA_LIVRAISON = "A_LA_LIVRAISON"        # client paie à la livraison


class Colis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "colis"

    voyage_id: Mapped[UUID] = mapped_column(ForeignKey("voyages.id"), nullable=False)
    expediteur_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    ville_depart: Mapped[str] = mapped_column(String(100))
    ville_arrivee: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    categorie: Mapped[ColisCategorie] = mapped_column(Enum(ColisCategorie))
    poids_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    fragile: Mapped[bool] = mapped_column(Boolean, default=False)
    destinataire_nom: Mapped[str] = mapped_column(String(100))
    destinataire_telephone: Mapped[str] = mapped_column(String(20))
    prix: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    modalite_paiement: Mapped[ColisModalitePaiement] = mapped_column(
        Enum(ColisModalitePaiement), default=ColisModalitePaiement.A_LA_LIVRAISON
    )
    statut: Mapped[ColisStatut] = mapped_column(Enum(ColisStatut), default=ColisStatut.EN_ATTENTE)
    code_suivi: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    expediteur = relationship("User", foreign_keys=[expediteur_id])
    voyage = relationship("Voyage", back_populates="colis")
    suivi = relationship("SuiviColis", back_populates="colis", order_by="SuiviColis.created_at")