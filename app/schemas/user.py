from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models.user import UserRole, UserStatus, GenreUser


class UserRead(BaseModel):
    id: UUID
    telephone: str
    email: str | None
    nom: str
    prenom: str
    photo_url: str | None
    genre: GenreUser
    role: UserRole
    statut: UserStatus
    telephone_verifie: bool
    note_moyenne: float
    nombre_avis: int
    langue: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    nom: str | None = None
    prenom: str | None = None
    email: str | None = None
    langue: str | None = None
    genre: GenreUser | None = None


class UserPublic(BaseModel):
    id: UUID
    nom: str
    prenom: str
    photo_url: str | None
    note_moyenne: float
    nombre_avis: int
    role: UserRole

    model_config = {"from_attributes": True}