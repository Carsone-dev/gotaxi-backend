from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.colis import ColisCategorie, ColisStatut, ColisModalitePaiement
from app.schemas.voyage import VoyageRead


class ColisCreate(BaseModel):
    voyage_id: UUID
    description: str = Field(..., max_length=500)
    categorie: ColisCategorie
    poids_kg: float | None = Field(None, gt=0, le=100)
    fragile: bool = False
    destinataire_nom: str = Field(..., max_length=100)
    destinataire_telephone: str = Field(..., max_length=20)
    modalite_paiement: ColisModalitePaiement = ColisModalitePaiement.A_LA_LIVRAISON


class ColisRead(BaseModel):
    id: UUID
    voyage_id: UUID
    expediteur_id: UUID
    ville_depart: str
    ville_arrivee: str
    description: str
    categorie: ColisCategorie
    poids_kg: float | None
    fragile: bool
    destinataire_nom: str
    destinataire_telephone: str
    prix: float | None
    modalite_paiement: ColisModalitePaiement
    statut: ColisStatut
    code_suivi: str
    photo_url: str | None
    voyage: VoyageRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}