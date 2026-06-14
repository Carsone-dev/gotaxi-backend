import uuid as uuid_pkg
from sqlalchemy import String, Boolean, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Gare(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "gares"

    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    ville_id: Mapped[uuid_pkg.UUID] = mapped_column(
        ForeignKey("villes.id", ondelete="CASCADE"), nullable=False
    )
    adresse: Mapped[str | None] = mapped_column(String(300), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    ville: Mapped["Ville"] = relationship("Ville", back_populates="gares")  # noqa: F821
