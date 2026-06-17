from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class AvisCreate(BaseModel):
    voyage_id: UUID
    note: int = Field(..., ge=1, le=5)
    commentaire: str | None = Field(None, max_length=1000)
    tags: list[str] = []


class AvisRead(BaseModel):
    id: UUID
    auteur_id: UUID
    cible_id: UUID
    voyage_id: UUID | None
    note: int
    commentaire: str | None
    tags: list
    signale: bool
    visible: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AvisPublicRead(AvisRead):
    auteur_prenom: str | None = None
    auteur_nom: str | None = None
    auteur_photo_url: str | None = None
