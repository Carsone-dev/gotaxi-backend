from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class AvisCreate(BaseModel):
    cible_id: UUID
    voyage_id: UUID | None = None
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