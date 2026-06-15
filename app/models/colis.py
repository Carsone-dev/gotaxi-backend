import enum
from datetime import datetime
from uuid import UUID
from sqlalchemy import String, Numeric, Integer, ForeignKey, Enum, Boolean, DateTime
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
    EN_ATTENTE_PAIEMENT = "EN_ATTENTE_PAIEMENT"  # frais plateforme non encore payés
    EN_ATTENTE = "EN_ATTENTE"                      # frais payés, visible aux chauffeurs
    CONFIRME = "CONFIRME"
    EN_TRANSIT = "EN_TRANSIT"
    LIVRE = "LIVRE"
    ANNULE = "ANNULE"


class ColisModalitePaiement(str, enum.Enum):
    """Conservé pour compatibilité avec les anciennes lignes en base."""
    A_LA_CONFIRMATION = "A_LA_CONFIRMATION"
    A_LA_LIVRAISON = "A_LA_LIVRAISON"


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
    # Prix indicatif du transport (négocié entre client et chauffeur, non géré par la plateforme)
    prix: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    statut: Mapped[ColisStatut] = mapped_column(Enum(ColisStatut), default=ColisStatut.EN_ATTENTE_PAIEMENT)
    code_suivi: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Frais de mise en relation collectés par la plateforme (100 FCFA)
    frais_plateforme: Mapped[int] = mapped_column(Integer, default=100)
    # Référence transaction FedaPay pour le paiement des frais
    fedapay_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Expiration du délai de paiement (15 min après création)
    paiement_expire_a: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Conservé nullable pour compatibilité historique
    modalite_paiement: Mapped[ColisModalitePaiement | None] = mapped_column(
        Enum(ColisModalitePaiement), nullable=True
    )

    expediteur = relationship("User", foreign_keys=[expediteur_id])
    voyage = relationship("Voyage", back_populates="colis")
    suivi = relationship("SuiviColis", back_populates="colis", order_by="SuiviColis.created_at")
