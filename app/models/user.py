import enum
from sqlalchemy import String, Boolean, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class UserRole(str, enum.Enum):
    CLIENT = "CLIENT"
    CHAUFFEUR = "CHAUFFEUR"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class UserStatus(str, enum.Enum):
    ACTIF = "ACTIF"
    SUSPENDU = "SUSPENDU"
    EN_ATTENTE_KYC = "EN_ATTENTE_KYC"
    SUPPRIME = "SUPPRIME"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    telephone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CLIENT)
    statut: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIF)
    telephone_verifie: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verifie: Mapped[bool] = mapped_column(Boolean, default=False)
    note_moyenne: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    nombre_avis: Mapped[int] = mapped_column(default=0)
    fcm_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    langue: Mapped[str] = mapped_column(String(5), default="fr")

    chauffeur = relationship("Chauffeur", back_populates="user", uselist=False)
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    reservations = relationship("Reservation", back_populates="client")