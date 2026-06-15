from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.voyage import VoyageStatut


class VehiculeMin(BaseModel):
    photo_url: str | None
    type_vehicule: str
    marque: str
    modele: str
    photos_interieures: list[str] = []
    model_config = {"from_attributes": True}


class VoyageCreate(BaseModel):
    ville_depart: str
    ville_arrivee: str
    point_depart: str
    point_arrivee: str
    lat_depart: float
    lng_depart: float
    lat_arrivee: float
    lng_arrivee: float
    date_depart: datetime
    prix_par_place: int = Field(..., ge=500, le=100000)
    nombre_places_total: int = Field(..., ge=1, le=8)
    accepte_colis: bool = True
    climatise: bool = False
    non_fumeur: bool = True
    vehicule_id: UUID


class VoyageUpdate(BaseModel):
    prix_par_place: int | None = Field(None, ge=500, le=100000)
    point_depart: str | None = None
    date_depart: datetime | None = None
    accepte_colis: bool | None = None
    non_fumeur: bool | None = None


class VoyageRead(BaseModel):
    id: UUID
    chauffeur_id: UUID
    vehicule_id: UUID
    ville_depart: str
    ville_arrivee: str
    point_depart: str
    point_arrivee: str
    date_depart: datetime
    date_arrivee_estimee: datetime
    prix_par_place: int
    nombre_places_restantes: int
    nombre_places_total: int
    accepte_colis: bool
    climatise: bool
    non_fumeur: bool
    statut: VoyageStatut
    distance_km: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VoyagePublicRead(VoyageRead):
    vehicule: VehiculeMin | None = None


class VoyageSearch(BaseModel):
    ville_depart: str
    ville_arrivee: str
    date_depart: date
    nombre_places: int = 1
    accepte_colis: bool | None = None
    climatise: bool | None = None
    prix_max: int | None = None
    sort_by: str = "depart_asc"