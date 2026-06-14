from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Ville(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "villes"

    nom: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    gares: Mapped[list["Gare"]] = relationship("Gare", back_populates="ville", cascade="all, delete-orphan")  # noqa: F821
