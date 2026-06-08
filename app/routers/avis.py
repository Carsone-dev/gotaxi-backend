from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.avis import Avis
from app.schemas.avis import AvisCreate, AvisRead
from app.schemas.common import MessageResponse, PaginatedResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/avis", tags=["Avis"])


@router.post("", response_model=AvisRead, status_code=201)
async def create_avis(
    payload: AvisCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.note < 1 or payload.note > 5:
        raise HTTPException(status_code=400, detail="Note doit être entre 1 et 5")

    avis = Avis(
        auteur_id=current_user.id,
        cible_id=payload.cible_id,
        voyage_id=payload.voyage_id,
        note=payload.note,
        commentaire=payload.commentaire,
        tags=payload.tags,
    )
    db.add(avis)
    await db.flush()

    cible = await db.get(User, payload.cible_id)
    if cible:
        all_avis_result = await db.execute(
            select(Avis).where(Avis.cible_id == payload.cible_id, Avis.visible == True)
        )
        all_avis = all_avis_result.scalars().all()
        if all_avis:
            cible.note_moyenne = sum(a.note for a in all_avis) / len(all_avis)
            cible.nombre_avis = len(all_avis)

    return avis


@router.get("/chauffeur/{chauffeur_id}", response_model=PaginatedResponse[AvisRead])
async def chauffeur_avis(
    chauffeur_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Avis)
        .where(Avis.cible_id == chauffeur_id, Avis.visible == True)
        .order_by(Avis.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()
    return PaginatedResponse(items=items, total=len(items), page=page, size=size, pages=1)


@router.get("/me/recus", response_model=list[AvisRead])
async def my_avis_recus(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Avis)
        .where(Avis.cible_id == current_user.id, Avis.visible == True)
        .order_by(Avis.created_at.desc())
    )
    return result.scalars().all()


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
    return {"message": "Avis signalé"}