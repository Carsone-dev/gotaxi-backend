from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.reservation import ReservationStatut
from app.schemas.voyage import VoyageRead
from app.schemas.user import UserPublic


class ReservationCreate(BaseModel):
    voyage_id: UUID
    nombre_places: int = Field(..., ge=1, le=8)


class ReservationRead(BaseModel):
    id: UUID
    voyage_id: UUID
    client_id: UUID
    nombre_places: int
    prix_total: int
    statut: ReservationStatut
    code_confirmation: str
    created_at: datetime
    voyage: VoyageRead | None = None
    client: UserPublic | None = None

    model_config = {"from_attributes": True}