from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.voyage import Voyage, VoyageStatut
from app.models.colis import Colis
from app.models.demande_chauffeur import DemandeInscriptionChauffeur
from app.schemas.voyage import VoyageRead
from app.schemas.colis import ColisRead
from app.schemas.common import PaginatedResponse, MessageResponse
from app.schemas.demande_chauffeur import DemandeChauffeurCreate

router = APIRouter(prefix="/public", tags=["Public"])

VILLES = [
    "Cotonou", "Porto-Novo", "Parakou", "Abomey-Calavi",
    "Bohicon", "Natitingou", "Kandi", "Lokossa",
    "Ouidah", "Abomey", "Djougou",
]


@router.get("/health")
async def health():
    return {"status": "ok", "service": "gotaxi-backend"}


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    await db.execute(select(func.now()))
    return {"status": "ok", "database": "connected"}


@router.get("/villes")
async def get_villes():
    return {"villes": VILLES}


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    count = await db.execute(select(func.count()).select_from(Voyage))
    return {
        "total_voyages": count.scalar() or 0,
        "villes_desservies": len(VILLES),
    }


@router.get("/voyages/search", response_model=PaginatedResponse[VoyageRead])
async def public_search_voyages(
    ville_depart: str = Query(...),
    ville_arrivee: str = Query(...),
    date_depart: date = Query(...),
    nombre_places: int = Query(1, ge=1),
    prix_max: int | None = Query(None),
    sort_by: str = Query("depart_asc"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Recherche publique de voyages (sans authentification)."""
    day_start = datetime(date_depart.year, date_depart.month, date_depart.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    filters = [
        Voyage.ville_depart.ilike(f"%{ville_depart}%"),
        Voyage.ville_arrivee.ilike(f"%{ville_arrivee}%"),
        Voyage.date_depart >= day_start,
        Voyage.date_depart < day_end,
        Voyage.nombre_places_restantes >= nombre_places,
        Voyage.statut == VoyageStatut.PUBLIE,
    ]
    if prix_max is not None:
        filters.append(Voyage.prix_par_place <= prix_max)

    sort_map = {
        "prix_asc": Voyage.prix_par_place.asc(),
        "prix_desc": Voyage.prix_par_place.desc(),
        "depart_asc": Voyage.date_depart.asc(),
        "depart_desc": Voyage.date_depart.desc(),
    }
    order = sort_map.get(sort_by, Voyage.date_depart.asc())

    total = (await db.execute(select(func.count(Voyage.id)).where(*filters))).scalar() or 0
    items = (
        await db.execute(
            select(Voyage).where(*filters).order_by(order).offset((page - 1) * size).limit(size)
        )
    ).scalars().all()

    pages = max(1, -(-total // size))
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("/demandes-chauffeur", response_model=MessageResponse, status_code=201)
async def submit_demande_chauffeur(
    payload: DemandeChauffeurCreate,
    db: AsyncSession = Depends(get_db),
):
    """Soumission publique d'une candidature chauffeur (sans authentification)."""
    demande = DemandeInscriptionChauffeur(**payload.model_dump())
    db.add(demande)
    await db.commit()
    return MessageResponse(message="Candidature reçue. Notre équipe vous contactera dans les 24h.")


@router.get("/colis/{code_suivi}", response_model=ColisRead)
async def public_track_colis(
    code_suivi: str,
    db: AsyncSession = Depends(get_db),
):
    """Suivi public d'un colis par son code de suivi (ex: GTX-ABC123)."""
    result = await db.execute(
        select(Colis)
        .options(selectinload(Colis.voyage))
        .where(Colis.code_suivi == code_suivi.upper())
    )
    colis = result.scalar_one_or_none()
    if not colis:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    return colis