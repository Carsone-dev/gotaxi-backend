import secrets
import string
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.chauffeur import Chauffeur
from app.models.colis import Colis, ColisStatut
from app.models.voyage import Voyage, VoyageStatut
from app.schemas.colis import ColisCreate, ColisRead
from app.dependencies import get_current_user
from app.services.colis_pricing import calculer_prix_colis

_STATUTS_COLIS_ACCEPTES = {VoyageStatut.PUBLIE, VoyageStatut.COMPLET, VoyageStatut.EN_COURS}

router = APIRouter(prefix="/colis", tags=["Colis"])


def _generate_code_suivi() -> str:
    chars = string.ascii_uppercase + string.digits
    return "GTX-" + "".join(secrets.choice(chars) for _ in range(6))


async def _get_chauffeur_or_403(user: User, db: AsyncSession) -> Chauffeur:
    result = await db.execute(select(Chauffeur).where(Chauffeur.user_id == user.id))
    chauffeur = result.scalar_one_or_none()
    if not chauffeur:
        raise HTTPException(status_code=403, detail="Profil chauffeur introuvable")
    return chauffeur


async def _get_colis_with_voyage(colis_id: UUID, db: AsyncSession) -> Colis:
    result = await db.execute(
        select(Colis).options(selectinload(Colis.voyage)).where(Colis.id == colis_id)
    )
    colis = result.scalar_one_or_none()
    if not colis:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    return colis


async def _reload_colis(colis_id: UUID, db: AsyncSession) -> Colis:
    result = await db.execute(
        select(Colis).options(selectinload(Colis.voyage)).where(Colis.id == colis_id)
    )
    return result.scalar_one()


def _require_statut(colis: Colis, expected: ColisStatut) -> None:
    if colis.statut != expected:
        raise HTTPException(
            status_code=409,
            detail=f"Action impossible : statut actuel '{colis.statut}', requis '{expected}'",
        )


async def _require_chauffeur_owns_voyage(colis: Colis, user: User, db: AsyncSession) -> None:
    chauffeur = await _get_chauffeur_or_403(user, db)
    if colis.voyage.chauffeur_id != chauffeur.id:
        raise HTTPException(status_code=403, detail="Ce colis ne fait pas partie de vos voyages")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Créer un colis (client)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=ColisRead, status_code=201)
async def create_colis(
    payload: ColisCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    voyage = await db.get(Voyage, payload.voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail="Voyage introuvable")
    if voyage.statut not in _STATUTS_COLIS_ACCEPTES:
        raise HTTPException(
            status_code=422,
            detail=f"Ce voyage ne peut plus accepter de colis (statut : {voyage.statut})",
        )
    if not voyage.accepte_colis:
        raise HTTPException(status_code=422, detail="Ce voyage n'accepte pas les colis")

    prix = calculer_prix_colis(
        categorie=payload.categorie,
        poids_kg=payload.poids_kg,
        fragile=payload.fragile,
        distance_km=voyage.distance_km,
        lat_depart=voyage.lat_depart,
        lng_depart=voyage.lng_depart,
        lat_arrivee=voyage.lat_arrivee,
        lng_arrivee=voyage.lng_arrivee,
    )

    colis = Colis(
        voyage_id=payload.voyage_id,
        expediteur_id=current_user.id,
        ville_depart=voyage.ville_depart,
        ville_arrivee=voyage.ville_arrivee,
        description=payload.description,
        categorie=payload.categorie,
        poids_kg=payload.poids_kg,
        fragile=payload.fragile,
        destinataire_nom=payload.destinataire_nom,
        destinataire_telephone=payload.destinataire_telephone,
        modalite_paiement=payload.modalite_paiement,
        statut=ColisStatut.EN_ATTENTE,
        code_suivi=_generate_code_suivi(),
        prix=prix,
        photo_url=None,
    )
    db.add(colis)
    await db.flush()

    result = await db.execute(
        select(Colis).options(selectinload(Colis.voyage)).where(Colis.id == colis.id)
    )
    return result.scalar_one()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Lister les colis du client connecté
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=list[ColisRead])
async def my_colis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Colis)
        .options(selectinload(Colis.voyage))
        .where(Colis.expediteur_id == current_user.id)
        .order_by(Colis.created_at.desc())
    )
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Colis d'un voyage (vue chauffeur)
# ─────────────────────────────────────────────────────────────────────────────
# Défini avant /{colis_id} pour éviter la collision de route

@router.get("/voyage/{voyage_id}", response_model=list[ColisRead])
async def colis_du_voyage(
    voyage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    voyage = await db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail="Voyage introuvable")

    chauffeur = await _get_chauffeur_or_403(current_user, db)
    if voyage.chauffeur_id != chauffeur.id:
        raise HTTPException(status_code=403, detail="Ce voyage ne vous appartient pas")

    result = await db.execute(
        select(Colis)
        .options(selectinload(Colis.voyage))
        .where(Colis.voyage_id == voyage_id)
        .order_by(Colis.created_at.desc())
    )
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Détail d'un colis
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{colis_id}", response_model=ColisRead)
async def get_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    colis = await _get_colis_with_voyage(colis_id, db)

    is_expediteur = colis.expediteur_id == current_user.id
    is_chauffeur_du_voyage = False
    if current_user.role == UserRole.CHAUFFEUR:
        result = await db.execute(select(Chauffeur.id).where(Chauffeur.user_id == current_user.id))
        chauffeur_id = result.scalar_one_or_none()
        if chauffeur_id and colis.voyage and colis.voyage.chauffeur_id == chauffeur_id:
            is_chauffeur_du_voyage = True

    if not is_expediteur and not is_chauffeur_du_voyage:
        raise HTTPException(status_code=403, detail="Accès refusé")

    return colis


# ─────────────────────────────────────────────────────────────────────────────
# 4. Annuler un colis (client ou chauffeur)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{colis_id}/annuler", response_model=ColisRead)
async def annuler_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    colis = await _get_colis_with_voyage(colis_id, db)
    _require_statut(colis, ColisStatut.EN_ATTENTE)

    is_expediteur = colis.expediteur_id == current_user.id
    is_chauffeur_du_voyage = False
    if current_user.role == UserRole.CHAUFFEUR:
        result = await db.execute(select(Chauffeur.id).where(Chauffeur.user_id == current_user.id))
        chauffeur_id = result.scalar_one_or_none()
        if chauffeur_id and colis.voyage and colis.voyage.chauffeur_id == chauffeur_id:
            is_chauffeur_du_voyage = True

    if not is_expediteur and not is_chauffeur_du_voyage:
        raise HTTPException(status_code=403, detail="Accès refusé")

    colis.statut = ColisStatut.ANNULE
    await db.flush()
    return await _reload_colis(colis.id, db)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Confirmer un colis (chauffeur accepte)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{colis_id}/confirmer", response_model=ColisRead)
async def confirmer_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    colis = await _get_colis_with_voyage(colis_id, db)
    _require_statut(colis, ColisStatut.EN_ATTENTE)
    await _require_chauffeur_owns_voyage(colis, current_user, db)

    colis.statut = ColisStatut.CONFIRME
    await db.flush()
    return await _reload_colis(colis.id, db)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Mettre en transit
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{colis_id}/en_transit", response_model=ColisRead)
async def mettre_en_transit(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    colis = await _get_colis_with_voyage(colis_id, db)
    _require_statut(colis, ColisStatut.CONFIRME)
    await _require_chauffeur_owns_voyage(colis, current_user, db)

    if colis.voyage.statut != VoyageStatut.EN_COURS:
        raise HTTPException(
            status_code=422,
            detail="Le voyage doit être EN_COURS pour mettre le colis en transit",
        )

    colis.statut = ColisStatut.EN_TRANSIT
    await db.flush()
    return await _reload_colis(colis.id, db)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Marquer comme livré
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{colis_id}/livrer", response_model=ColisRead)
async def livrer_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    colis = await _get_colis_with_voyage(colis_id, db)
    _require_statut(colis, ColisStatut.EN_TRANSIT)
    await _require_chauffeur_owns_voyage(colis, current_user, db)

    colis.statut = ColisStatut.LIVRE
    await db.flush()
    return await _reload_colis(colis.id, db)