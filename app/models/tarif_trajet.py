import uuid as uuid_pkg
from sqlalchemy import Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class TarifTrajet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tarifs_trajets"
    __table_args__ = (
        UniqueConstraint("ville_depart_id", "ville_arrivee_id", name="uq_tarif_route"),
    )

    ville_depart_id: Mapped[uuid_pkg.UUID] = mapped_column(
        ForeignKey("villes.id", ondelete="CASCADE"), nullable=False
    )
    ville_arrivee_id: Mapped[uuid_pkg.UUID] = mapped_column(
        ForeignKey("villes.id", ondelete="CASCADE"), nullable=False
    )
    prix_recommande: Mapped[int] = mapped_column(Integer, nullable=False)
    prix_max: Mapped[int] = mapped_column(Integer, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    ville_depart: Mapped["Ville"] = relationship("Ville", foreign_keys=[ville_depart_id])  # noqa: F821
    ville_arrivee: Mapped["Ville"] = relationship("Ville", foreign_keys=[ville_arrivee_id])  # noqa: F821
