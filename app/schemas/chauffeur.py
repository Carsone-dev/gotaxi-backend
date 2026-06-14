from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field
from app.models.vehicule import TypeVehicule


class VehiculeCreate(BaseModel):
    marque: str
    modele: str
    annee: int = Field(..., ge=2000, le=2030)
    immatriculation: str
    couleur: str
    type_vehicule: TypeVehicule
    nombre_places: int = Field(..., ge=1, le=20)
    climatise: bool = False


class VehiculeUpdate(BaseModel):
    marque: str | None = None
    modele: str | None = None
    annee: int | None = Field(None, ge=2000, le=2030)
    couleur: str | None = None
    nombre_places: int | None = Field(None, ge=1, le=20)
    climatise: bool | None = None


class VehiculeRead(BaseModel):
    id: UUID
    marque: str
    modele: str
    annee: int
    immatriculation: str
    couleur: str
    type_vehicule: TypeVehicule
    nombre_places: int
    climatise: bool
    photo_url: str | None
    actif: bool

    model_config = {"from_attributes": True}


class ChauffeurRead(BaseModel):
    id: UUID
    user_id: UUID
    cin_numero: str | None
    cin_url: str | None
    permis_numero: str | None
    permis_url: str | None
    permis_expiration: date | None
    casier_judiciaire_url: str | None
    kyc_valide: bool
    kyc_valide_le: date | None
    autorisation_transfrontaliere: bool
    en_ligne: bool
    derniere_position_lat: float | None
    derniere_position_lng: float | None
    nombre_trajets: int
    revenus_total: int
    vehicules: list[VehiculeRead] = []

    model_config = {"from_attributes": True}


class ChauffeurUpdate(BaseModel):
    cin_numero: str | None = None
    permis_numero: str | None = None
    permis_expiration: date | None = None


class PositionUpdate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    vitesse: float | None = None
    heading: float | None = None


class ChauffeurPublic(BaseModel):
    id: UUID
    nom: str
    prenom: str
    photo_url: str | None
    note_moyenne: float
    nombre_avis: int
    nombre_trajets: int
    en_ligne: bool

    model_config = {"from_attributes": True}


class RevenusRead(BaseModel):
    aujourd_hui: int
    semaine: int
    mois: int
    total: int


class ChauffeurStats(BaseModel):
    nombre_trajets: int
    revenus_total: int
    note_moyenne: float
    nombre_avis: int
    en_ligne: bool