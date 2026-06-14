from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.ville import VilleRead


class TarifTrajetCreate(BaseModel):
    ville_depart_id: UUID
    ville_arrivee_id: UUID
    prix_recommande: int = Field(..., ge=500)
    prix_max: int = Field(..., ge=500)


class TarifTrajetUpdate(BaseModel):
    prix_recommande: int | None = Field(None, ge=500)
    prix_max: int | None = Field(None, ge=500)
    actif: bool | None = None


class TarifTrajetRead(BaseModel):
    id: UUID
    ville_depart_id: UUID
    ville_arrivee_id: UUID
    ville_depart: VilleRead
    ville_arrivee: VilleRead
    prix_recommande: int
    prix_max: int
    actif: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
