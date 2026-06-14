from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.chauffeur import Chauffeur
from app.models.payout_account import ComptePayoutChauffeur
from app.schemas.payout_account import ComptePayoutCreate, ComptePayoutRead
from app.schemas.common import MessageResponse
from app.dependencies import require_role

router = APIRouter(prefix="/chauffeurs/me/payout-account", tags=["Payout Account"])

require_chauffeur = require_role(UserRole.CHAUFFEUR)


async def _get_chauffeur_or_404(user: User, db: AsyncSession) -> Chauffeur:
    result = await db.execute(select(Chauffeur).where(Chauffeur.user_id == user.id))
    chauffeur = result.scalar_one_or_none()
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Profil chauffeur introuvable")
    return chauffeur


@router.get("", response_model=ComptePayoutRead)
async def get_payout_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    result = await db.execute(
        select(ComptePayoutChauffeur).where(ComptePayoutChauffeur.chauffeur_id == chauffeur.id)
    )
    compte = result.scalar_one_or_none()
    if not compte:
        raise HTTPException(status_code=404, detail="Aucun compte payout configuré")
    return compte


@router.put("", response_model=ComptePayoutRead)
async def upsert_payout_account(
    payload: ComptePayoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    """Crée ou remplace le compte payout du chauffeur connecté.

    Un chauffeur ne peut avoir qu'un seul compte. Le numéro de téléphone doit
    être unique sur l'ensemble des chauffeurs de la plateforme.
    """
    chauffeur = await _get_chauffeur_or_404(current_user, db)

    result = await db.execute(
        select(ComptePayoutChauffeur).where(ComptePayoutChauffeur.chauffeur_id == chauffeur.id)
    )
    compte = result.scalar_one_or_none()

    if compte:
        compte.operateur = payload.operateur
        compte.telephone = payload.telephone
        compte.actif = True
    else:
        compte = ComptePayoutChauffeur(
            chauffeur_id=chauffeur.id,
            operateur=payload.operateur,
            telephone=payload.telephone,
        )
        db.add(compte)

    try:
        await db.commit()
        await db.refresh(compte)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ce numéro est déjà utilisé par un autre chauffeur",
        )

    return compte


@router.delete("", response_model=MessageResponse)
async def delete_payout_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    result = await db.execute(
        select(ComptePayoutChauffeur).where(ComptePayoutChauffeur.chauffeur_id == chauffeur.id)
    )
    compte = result.scalar_one_or_none()
    if not compte:
        raise HTTPException(status_code=404, detail="Aucun compte payout à supprimer")
    await db.delete(compte)
    await db.commit()
    return {"message": "Compte payout supprimé"}
