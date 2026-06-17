from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import User
from app.models.chauffeur import Chauffeur
from app.models.avis import Avis
from app.models.voyage import Voyage, VoyageStatut
from app.models.reservation import Reservation, ReservationStatut
from app.schemas.avis import AvisCreate, AvisRead, AvisPublicRead
from app.schemas.common import MessageResponse, PaginatedResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/avis", tags=["Avis"])


@router.post("", response_model=AvisRead, status_code=201)
async def create_avis(
    payload: AvisCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    voyage = await db.get(Voyage, payload.voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail="Voyage introuvable")

    if voyage.statut != VoyageStatut.TERMINE:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez laisser un avis que pour un voyage terminé",
        )

    reservation = (await db.execute(
        select(Reservation).where(
            Reservation.voyage_id == payload.voyage_id,
            Reservation.client_id == current_user.id,
            Reservation.statut == ReservationStatut.TERMINEE,
        )
    )).scalar_one_or_none()
    if not reservation:
        raise HTTPException(
            status_code=403,
            detail="Vous n'étiez pas passager de ce voyage ou votre réservation n'est pas terminée",
        )

    existing = (await db.execute(
        select(Avis).where(
            Avis.auteur_id == current_user.id,
            Avis.voyage_id == payload.voyage_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Vous avez déjà laissé un avis pour ce voyage")

    chauffeur = await db.get(Chauffeur, voyage.chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")

    avis = Avis(
        auteur_id=current_user.id,
        cible_id=chauffeur.user_id,
        voyage_id=payload.voyage_id,
        note=payload.note,
        commentaire=payload.commentaire,
        tags=payload.tags,
    )
    db.add(avis)
    await db.flush()

    cible = await db.get(User, chauffeur.user_id)
    if cible:
        all_avis = (await db.execute(
            select(Avis).where(Avis.cible_id == chauffeur.user_id, Avis.visible == True)
        )).scalars().all()
        cible.note_moyenne = sum(a.note for a in all_avis) / len(all_avis)
        cible.nombre_avis = len(all_avis)

    await db.commit()
    await db.refresh(avis)
    return avis


@router.get("/chauffeur/{chauffeur_user_id}", response_model=PaginatedResponse[AvisPublicRead])
async def chauffeur_avis(
    chauffeur_user_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(
        select(func.count()).select_from(Avis).where(
            Avis.cible_id == chauffeur_user_id,
            Avis.visible == True,
        )
    )).scalar() or 0

    result = await db.execute(
        select(Avis)
        .where(Avis.cible_id == chauffeur_user_id, Avis.visible == True)
        .order_by(Avis.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    avis_list = result.scalars().all()

    auteur_ids = list({a.auteur_id for a in avis_list})
    auteurs: dict[UUID, User] = {}
    if auteur_ids:
        auteurs_result = await db.execute(select(User).where(User.id.in_(auteur_ids)))
        auteurs = {u.id: u for u in auteurs_result.scalars().all()}

    items = []
    for a in avis_list:
        auteur = auteurs.get(a.auteur_id)
        item = AvisPublicRead.model_validate(a)
        if auteur:
            item.auteur_prenom = auteur.prenom
            item.auteur_nom = auteur.nom
            item.auteur_photo_url = auteur.photo_url
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=max(1, -(-total // size)),
    )


@router.post("/{avis_id}/signaler", response_model=MessageResponse)
async def signaler_avis(
    avis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    avis = await db.get(Avis, avis_id)
    if not avis:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    avis.signale = True
    await db.commit()
    return {"message": "Avis signalé"}
