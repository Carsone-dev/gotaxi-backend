from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class VilleCreate(BaseModel):
    nom: str = Field(..., min_length=2, max_length=100)


class VilleUpdate(BaseModel):
    nom: str | None = Field(None, min_length=2, max_length=100)
    actif: bool | None = None


class VilleRead(BaseModel):
    id: UUID
    nom: str
    actif: bool
    created_at: datetime

    model_config = {"from_attributes": True}
