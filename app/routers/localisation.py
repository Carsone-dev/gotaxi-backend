from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.ville import Ville
from app.models.gare import Gare
from app.schemas.ville import VilleRead
from app.schemas.gare import GareRead

router = APIRouter(tags=["Localisation"])


@router.get("/villes", response_model=list[VilleRead])
async def list_villes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Ville).where(Ville.actif == True).order_by(Ville.nom)
    )
    return result.scalars().all()


@router.get("/gares", response_model=list[GareRead])
async def list_gares(
    ville_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    filters = [Gare.actif == True]
    if ville_id:
        filters.append(Gare.ville_id == ville_id)
    result = await db.execute(
        select(Gare)
        .options(selectinload(Gare.ville))
        .where(*filters)
        .order_by(Gare.nom)
    )
    return result.scalars().all()
