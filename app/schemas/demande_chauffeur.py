from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator
from app.models.demande_chauffeur import DemandeStatut


class DemandeChauffeurCreate(BaseModel):
    prenom: str
    nom: str
    telephone: str
    ville: str
    vehicule: str
    message: str | None = None

    @field_validator("telephone")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        return v.strip()


class DemandeChauffeurRead(BaseModel):
    id: UUID
    prenom: str
    nom: str
    telephone: str
    ville: str
    vehicule: str
    message: str | None
    statut: DemandeStatut
    traite_le: datetime | None
    traite_par_id: UUID | None
    user_id: UUID | None
    motif_rejet: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RejeterDemandeRequest(BaseModel):
    motif: str | None = None


class TraiterDemandeCredentials(BaseModel):
    telephone: str
    password: str
    user_id: str


class TraiterDemandeResponse(BaseModel):
    message: str
    credentials: TraiterDemandeCredentials
