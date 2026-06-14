from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.ville import VilleRead


class GareCreate(BaseModel):
    nom: str = Field(..., min_length=2, max_length=200)
    ville_id: UUID
    adresse: str | None = Field(None, max_length=300)
    lat: float | None = None
    lng: float | None = None


class GareUpdate(BaseModel):
    nom: str | None = Field(None, min_length=2, max_length=200)
    adresse: str | None = None
    lat: float | None = None
    lng: float | None = None
    actif: bool | None = None


class GareRead(BaseModel):
    id: UUID
    nom: str
    ville_id: UUID
    ville: VilleRead
    adresse: str | None
    lat: float | None
    lng: float | None
    actif: bool
    created_at: datetime

    model_config = {"from_attributes": True}
