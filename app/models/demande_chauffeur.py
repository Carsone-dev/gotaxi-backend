import enum
from datetime import datetime
from uuid import UUID
from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class DemandeStatut(str, enum.Enum):
    NOUVELLE = "NOUVELLE"
    EN_COURS = "EN_COURS"
    TRAITEE = "TRAITEE"
    REJETEE = "REJETEE"


class DemandeInscriptionChauffeur(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "demandes_inscription_chauffeur"

    prenom: Mapped[str] = mapped_column(String(100))
    nom: Mapped[str] = mapped_column(String(100))
    telephone: Mapped[str] = mapped_column(String(20), index=True)
    ville: Mapped[str] = mapped_column(String(100))
    vehicule: Mapped[str] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    statut: Mapped[DemandeStatut] = mapped_column(
        SAEnum(DemandeStatut), default=DemandeStatut.NOUVELLE
    )

    traite_par_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    traite_le: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    motif_rejet: Mapped[str | None] = mapped_column(Text, nullable=True)

    traite_par = relationship("User", foreign_keys=[traite_par_id])
    user = relationship("User", foreign_keys=[user_id])
