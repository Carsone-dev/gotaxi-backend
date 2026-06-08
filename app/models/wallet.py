from uuid import UUID
from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Wallet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wallets"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    solde: Mapped[int] = mapped_column(Integer, default=0)
    devise: Mapped[str] = mapped_column(String(3), default="XOF")
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    user = relationship("User", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet")