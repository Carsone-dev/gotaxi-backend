import enum
from uuid import UUID
from sqlalchemy import String, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class NotifType(str, enum.Enum):
    RESERVATION = "RESERVATION"
    VOYAGE = "VOYAGE"
    COLIS = "COLIS"
    PAIEMENT = "PAIEMENT"
    SYSTEME = "SYSTEME"


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    type: Mapped[NotifType] = mapped_column(Enum(NotifType))
    titre: Mapped[str] = mapped_column(String(255))
    corps: Mapped[str] = mapped_column(String(1000))
    lue: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user = relationship("User")