from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.tarif_trajet import TarifTrajet
from app.models.ville import Ville
from app.schemas.tarif_trajet import TarifTrajetCreate, TarifTrajetUpdate, TarifTrajetRead
from app.schemas.common import MessageResponse
from app.dependencies import get_current_user, require_role

router = APIRouter(tags=["Tarifs"])

require_admin = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)

_load = [selectinload(TarifTrajet.ville_depart), selectinload(TarifTrajet.ville_arrivee)]


# ── Chauffeur / client ────────────────────────────────────────────────────────

@router.get("/tarifs", response_model=TarifTrajetRead | None)
async def get_tarif_for_route(
    ville_depart_id: UUID = Query(...),
    ville_arrivee_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TarifTrajet).options(*_load).where(
            TarifTrajet.ville_depart_id == ville_depart_id,
            TarifTrajet.ville_arrivee_id == ville_arrivee_id,
            TarifTrajet.actif == True,
        )
    )
    return result.scalar_one_or_none()


# ── Admin CRUD ────────────────────────────────────────────────────────────────

@router.get("/admin/tarifs", response_model=list[TarifTrajetRead])
async def list_tarifs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(TarifTrajet).options(*_load).join(
            Ville, TarifTrajet.ville_depart_id == Ville.id
        ).order_by(Ville.nom)
    )
    return result.scalars().all()


@router.post("/admin/tarifs", response_model=TarifTrajetRead, status_code=201)
async def create_tarif(
    payload: TarifTrajetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if payload.prix_recommande > payload.prix_max:
        raise HTTPException(status_code=400, detail="prix_recommande ne peut pas dépasser prix_max")
    if payload.ville_depart_id == payload.ville_arrivee_id:
        raise HTTPException(status_code=400, detail="Les villes de départ et d'arrivée doivent être différentes")

    vd = await db.get(Ville, payload.ville_depart_id)
    va = await db.get(Ville, payload.ville_arrivee_id)
    if not vd:
        raise HTTPException(status_code=404, detail="Ville de départ introuvable")
    if not va:
        raise HTTPException(status_code=404, detail="Ville d'arrivée introuvable")

    existing = await db.execute(
        select(TarifTrajet).where(
            TarifTrajet.ville_depart_id == payload.ville_depart_id,
            TarifTrajet.ville_arrivee_id == payload.ville_arrivee_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Un tarif existe déjà pour cette route")

    tarif = TarifTrajet(**payload.model_dump())
    db.add(tarif)
    await db.commit()
    await db.refresh(tarif, attribute_names=["ville_depart", "ville_arrivee"])
    return tarif


@router.patch("/admin/tarifs/{tarif_id}", response_model=TarifTrajetRead)
async def update_tarif(
    tarif_id: UUID,
    payload: TarifTrajetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(TarifTrajet).options(*_load).where(TarifTrajet.id == tarif_id)
    )
    tarif = result.scalar_one_or_none()
    if not tarif:
        raise HTTPException(status_code=404, detail="Tarif introuvable")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(tarif, field, value)
    if tarif.prix_recommande > tarif.prix_max:
        raise HTTPException(status_code=400, detail="prix_recommande ne peut pas dépasser prix_max")
    await db.commit()
    await db.refresh(tarif, attribute_names=["ville_depart", "ville_arrivee"])
    return tarif


@router.delete("/admin/tarifs/{tarif_id}", response_model=MessageResponse)
async def delete_tarif(
    tarif_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    tarif = await db.get(TarifTrajet, tarif_id)
    if not tarif:
        raise HTTPException(status_code=404, detail="Tarif introuvable")
    await db.delete(tarif)
    await db.commit()
    return {"message": "Tarif supprimé"}
