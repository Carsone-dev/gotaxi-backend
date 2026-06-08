from uuid import UUID
from sqlalchemy import Integer, ForeignKey, String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Avis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "avis"

    auteur_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    cible_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    voyage_id: Mapped[UUID | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    note: Mapped[int] = mapped_column(Integer)
    commentaire: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    signale: Mapped[bool] = mapped_column(Boolean, default=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)

    auteur = relationship("User", foreign_keys=[auteur_id])
    cible = relationship("User", foreign_keys=[cible_id])