from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.reservation import ReservationStatut
from app.schemas.voyage import VoyageRead
from app.schemas.user import UserPublic


class ReservationCreate(BaseModel):
    voyage_id: UUID
    nombre_places: int = Field(..., ge=1, le=8)


class InitierPaiementPayload(BaseModel):
    telephone: str = Field(..., min_length=8, max_length=20)


class ReservationRead(BaseModel):
    id: UUID
    voyage_id: UUID
    client_id: UUID
    nombre_places: int
    prix_total: int
    frais_plateforme: int
    statut: ReservationStatut
    code_confirmation: str
    paiement_expire_a: datetime | None = None
    created_at: datetime
    voyage: VoyageRead | None = None
    client: UserPublic | None = None

    model_config = {"from_attributes": True}


class PaiementStatutRead(BaseModel):
    statut: str  # 'confirme' | 'en_attente' | 'echec' | 'expire' | 'non_initie'
    reservation_statut: ReservationStatut
