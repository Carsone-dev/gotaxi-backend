from uuid import UUID
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update as sa_update
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.chauffeur import Chauffeur
from app.models.voyage import Voyage, VoyageStatut
from app.models.vehicule import Vehicule
from app.models.reservation import Reservation, ReservationStatut
from app.schemas.voyage import VoyageCreate, VoyageRead, VoyageUpdate
from app.schemas.reservation import ReservationRead
from app.schemas.common import PaginatedResponse, MessageResponse
from app.dependencies import get_current_user, require_role
from app.exceptions import KYCNotValidatedException
from app.models.tarif_trajet import TarifTrajet
from app.models.ville import Ville
from app.services.payout import payer_chauffeur

router = APIRouter(prefix="/voyages", tags=["Voyages"])

require_chauffeur = require_role(UserRole.CHAUFFEUR)


async def _get_chauffeur_id_or_404(user: User, db: AsyncSession) -> UUID:
    result = await db.execute(select(Chauffeur.id).where(Chauffeur.user_id == user.id))
    chauffeur_id = result.scalar_one_or_none()
    if not chauffeur_id:
        raise HTTPException(status_code=404, detail="Profil chauffeur introuvable")
    return chauffeur_id


async def _get_voyage_owned_or_403(
    voyage_id: UUID,
    chauffeur_id: UUID,
    db: AsyncSession,
) -> Voyage:
    voyage = await db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail="Voyage introuvable")
    if voyage.chauffeur_id != chauffeur_id:
        raise HTTPException(status_code=403, detail="Ce voyage ne vous appartient pas")
    return voyage


@router.get("/search", response_model=PaginatedResponse[VoyageRead])
async def search_voyages(
    ville_depart: str = Query(...),
    ville_arrivee: str = Query(...),
    date_depart: date = Query(...),
    nombre_places: int = Query(1, ge=1),
    accepte_colis: bool | None = Query(None),
    climatise: bool | None = Query(None),
    prix_max: int | None = Query(None),
    sort_by: str = Query("depart_asc"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    day_start = datetime(date_depart.year, date_depart.month, date_depart.day, tzinfo=timezone.utc)

    filters = [
        Voyage.ville_depart.ilike(f"%{ville_depart}%"),
        Voyage.ville_arrivee.ilike(f"%{ville_arrivee}%"),
        Voyage.date_depart >= day_start,
        Voyage.nombre_places_restantes >= nombre_places,
        Voyage.statut == VoyageStatut.PUBLIE,
    ]
    if accepte_colis is not None:
        filters.append(Voyage.accepte_colis == accepte_colis)
    if climatise is not None:
        filters.append(Voyage.climatise == climatise)
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


@router.get("/colis-search", response_model=PaginatedResponse[VoyageRead])
async def search_voyages_pour_colis(
    ville_depart: str = Query(...),
    ville_arrivee: str = Query(...),
    date_depart: date = Query(...),
    sort_by: str = Query("depart_asc"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recherche de voyages disponibles pour envoyer un colis.
    Retourne les voyages PUBLIE + COMPLET + EN_COURS qui acceptent les colis.
    Pas de filtre sur les places restantes (le colis ne prend pas de place passager)."""
    day_start = datetime(date_depart.year, date_depart.month, date_depart.day, tzinfo=timezone.utc)

    filters = [
        Voyage.ville_depart.ilike(f"%{ville_depart}%"),
        Voyage.ville_arrivee.ilike(f"%{ville_arrivee}%"),
        Voyage.date_depart >= day_start,
        Voyage.accepte_colis == True,
        Voyage.statut.in_([VoyageStatut.PUBLIE, VoyageStatut.COMPLET, VoyageStatut.EN_COURS]),
    ]

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


@router.get("/popular", response_model=list[VoyageRead])
async def popular_voyages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Voyage)
        .where(Voyage.statut == VoyageStatut.PUBLIE)
        .order_by(Voyage.date_depart.asc())
        .limit(10)
    )
    return result.scalars().all()


@router.get("/active", response_model=list[VoyageRead])
async def active_voyages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Voyages EN_COURS — affichage carte en temps réel."""
    result = await db.execute(
        select(Voyage)
        .where(Voyage.statut == VoyageStatut.EN_COURS)
        .order_by(Voyage.date_depart.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/me", response_model=list[VoyageRead])
async def my_voyages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur_id = await _get_chauffeur_id_or_404(current_user, db)
    result = await db.execute(
        select(Voyage)
        .where(Voyage.chauffeur_id == chauffeur_id)
        .order_by(Voyage.date_depart.desc())
    )
    return result.scalars().all()


@router.post("", response_model=VoyageRead, status_code=201)
async def create_voyage(
    payload: VoyageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    result = await db.execute(select(Chauffeur).where(Chauffeur.user_id == current_user.id))
    chauffeur = result.scalar_one_or_none()
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Profil chauffeur introuvable")
    if not chauffeur.kyc_valide:
        raise KYCNotValidatedException()
    if not chauffeur.en_ligne:
        raise HTTPException(status_code=403, detail="Vous devez être en ligne pour publier un trajet")

    vehicule = await db.get(Vehicule, payload.vehicule_id)
    if not vehicule or vehicule.chauffeur_id != chauffeur.id or not vehicule.actif:
        raise HTTPException(status_code=404, detail="Véhicule introuvable ou inactif")

    tarif_result = await db.execute(
        select(TarifTrajet).where(
            TarifTrajet.ville_depart.has(Ville.nom == payload.ville_depart),
            TarifTrajet.ville_arrivee.has(Ville.nom == payload.ville_arrivee),
            TarifTrajet.actif == True,
        )
    )
    tarif = tarif_result.scalar_one_or_none()
    if tarif and payload.prix_par_place > tarif.prix_max:
        raise HTTPException(
            status_code=400,
            detail=f"Prix maximum autorisé pour ce trajet : {tarif.prix_max} FCFA",
        )

    voyage = Voyage(
        **payload.model_dump(),
        chauffeur_id=chauffeur.id,
        nombre_places_restantes=payload.nombre_places_total,
        date_arrivee_estimee=payload.date_depart,
    )
    db.add(voyage)
    await db.commit()
    await db.refresh(voyage)
    return voyage


@router.get("/{voyage_id}/reservations", response_model=list[ReservationRead])
async def get_voyage_reservations(
    voyage_id: UUID,
    statut: ReservationStatut | None = Query(None, description="Filtrer par statut"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    """Chauffeur : toutes les réservations du voyage (toutes statuts) avec info client.
    Paramètre optionnel ?statut=EN_ATTENTE|CONFIRMEE|REFUSEE|ANNULEE|TERMINEE"""
    chauffeur_id = await _get_chauffeur_id_or_404(current_user, db)
    voyage = await db.get(Voyage, voyage_id)
    if not voyage or voyage.chauffeur_id != chauffeur_id:
        raise HTTPException(status_code=404, detail="Voyage introuvable")

    query = (
        select(Reservation)
        .options(selectinload(Reservation.client), selectinload(Reservation.voyage))
        .where(Reservation.voyage_id == voyage_id)
    )
    if statut:
        query = query.where(Reservation.statut == statut)
    query = query.order_by(Reservation.created_at.asc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{voyage_id}/passagers", response_model=list[ReservationRead])
async def get_passagers(
    voyage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    """Chauffeur : passagers confirmés uniquement (CONFIRMEE) avec info client."""
    chauffeur_id = await _get_chauffeur_id_or_404(current_user, db)
    voyage = await db.get(Voyage, voyage_id)
    if not voyage or voyage.chauffeur_id != chauffeur_id:
        raise HTTPException(status_code=404, detail="Voyage introuvable")
    result = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.client))
        .where(
            Reservation.voyage_id == voyage_id,
            Reservation.statut == ReservationStatut.CONFIRMEE,
        )
        .order_by(Reservation.created_at.asc())
    )
    return result.scalars().all()


@router.post("/{voyage_id}/start", response_model=MessageResponse)
async def start_voyage(
    voyage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur_id = await _get_chauffeur_id_or_404(current_user, db)
    voyage = await _get_voyage_owned_or_403(voyage_id, chauffeur_id, db)
    if voyage.statut not in (VoyageStatut.PUBLIE, VoyageStatut.COMPLET):
        raise HTTPException(status_code=400, detail="Seul un voyage PUBLIE ou COMPLET peut être démarré")
    voyage.statut = VoyageStatut.EN_COURS
    await db.commit()
    return {"message": "Voyage démarré"}


@router.post("/{voyage_id}/end", response_model=MessageResponse)
async def end_voyage(
    voyage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur_id = await _get_chauffeur_id_or_404(current_user, db)
    voyage = await _get_voyage_owned_or_403(voyage_id, chauffeur_id, db)
    if voyage.statut != VoyageStatut.EN_COURS:
        raise HTTPException(status_code=400, detail="Seul un voyage EN_COURS peut être terminé")

    # Récupérer les réservations CONFIRMEE pour calculer le montant à reverser
    resa_result = await db.execute(
        select(Reservation).where(
            Reservation.voyage_id == voyage_id,
            Reservation.statut == ReservationStatut.CONFIRMEE,
        )
    )
    reservations_confirmees = resa_result.scalars().all()
    montant_total = sum(r.prix_total for r in reservations_confirmees)

    voyage.statut = VoyageStatut.TERMINE
    await db.execute(
        sa_update(Reservation)
        .where(
            Reservation.voyage_id == voyage_id,
            Reservation.statut == ReservationStatut.CONFIRMEE,
        )
        .values(statut=ReservationStatut.TERMINEE)
    )

    # Charger le chauffeur complet pour le payout
    chauffeur_result = await db.execute(select(Chauffeur).where(Chauffeur.id == chauffeur_id))
    chauffeur = chauffeur_result.scalar_one()
    chauffeur.nombre_trajets += 1

    if montant_total > 0:
        await payer_chauffeur(
            chauffeur=chauffeur,
            montant=montant_total,
            db=db,
            description=f"Reversement voyage {voyage_id}",
        )

    await db.commit()
    return {"message": "Voyage terminé"}


@router.post("/{voyage_id}/cancel", response_model=MessageResponse)
async def cancel_voyage(
    voyage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur_id = await _get_chauffeur_id_or_404(current_user, db)
    voyage = await _get_voyage_owned_or_403(voyage_id, chauffeur_id, db)
    if voyage.statut not in (VoyageStatut.PUBLIE, VoyageStatut.COMPLET):
        raise HTTPException(status_code=400, detail="Seul un voyage PUBLIE ou COMPLET peut être annulé")
    await db.execute(
        sa_update(Reservation)
        .where(
            Reservation.voyage_id == voyage_id,
            Reservation.statut.in_([ReservationStatut.EN_ATTENTE, ReservationStatut.CONFIRMEE]),
        )
        .values(statut=ReservationStatut.ANNULEE)
    )
    voyage.statut = VoyageStatut.ANNULE
    await db.commit()
    return {"message": "Voyage annulé"}


@router.patch("/{voyage_id}", response_model=VoyageRead)
async def update_voyage(
    voyage_id: UUID,
    payload: VoyageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur_id = await _get_chauffeur_id_or_404(current_user, db)
    voyage = await _get_voyage_owned_or_403(voyage_id, chauffeur_id, db)
    if voyage.statut != VoyageStatut.PUBLIE:
        raise HTTPException(status_code=400, detail="Seul un voyage PUBLIE peut être modifié")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(voyage, field, value)
    await db.commit()
    await db.refresh(voyage)
    return voyage


@router.get("/{voyage_id}", response_model=VoyageRead)
async def get_voyage(
    voyage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Détail d'un voyage.
    - Chauffeur : uniquement son propre voyage.
    - Client : voyage PUBLIE ou COMPLET librement ; EN_COURS/TERMINE si réservation active dessus.
    """
    voyage = await db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail="Voyage introuvable")

    if current_user.role == UserRole.CHAUFFEUR:
        chauffeur_id = await _get_chauffeur_id_or_404(current_user, db)
        if voyage.chauffeur_id != chauffeur_id:
            raise HTTPException(status_code=403, detail="Ce voyage ne vous appartient pas")

    elif current_user.role == UserRole.CLIENT:
        if voyage.statut in (VoyageStatut.PUBLIE, VoyageStatut.COMPLET):
            pass  # librement accessible
        else:
            # Accès autorisé uniquement si le client a une réservation active sur ce voyage
            resa = await db.execute(
                select(Reservation.id).where(
                    Reservation.voyage_id == voyage_id,
                    Reservation.client_id == current_user.id,
                    Reservation.statut.in_([
                        ReservationStatut.EN_ATTENTE,
                        ReservationStatut.CONFIRMEE,
                        ReservationStatut.TERMINEE,
                    ]),
                )
            )
            if not resa.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Voyage introuvable")

    return voyage