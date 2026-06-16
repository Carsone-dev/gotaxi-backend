import secrets
import string
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.chauffeur import Chauffeur
from app.models.colis import Colis, ColisStatut
from app.models.voyage import Voyage, VoyageStatut
from app.schemas.colis import ColisCreate, ColisRead, ColisPaiementStatutRead
from app.schemas.reservation import InitierPaiementPayload
from app.dependencies import get_current_user
from app.services.colis_pricing import calculer_prix_colis
from app.services.frais_plateforme import (
    initier_paiement_colis,
    verifier_et_confirmer_colis,
    FRAIS_COLIS_PLATEFORME,
    PAIEMENT_EXPIRATION_MINUTES,
)

_MEDIA_DIR = Path(__file__).resolve().parents[2] / "media" / "colis"
_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
_MAX_SIZE_BYTES = 8 * 1024 * 1024  # 8 Mo

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
# 1. Créer un colis → EN_ATTENTE_PAIEMENT
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

    expire_a = datetime.now(timezone.utc) + timedelta(minutes=PAIEMENT_EXPIRATION_MINUTES)

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
        statut=ColisStatut.EN_ATTENTE_PAIEMENT,
        frais_plateforme=FRAIS_COLIS_PLATEFORME,
        paiement_expire_a=expire_a,
        code_suivi=_generate_code_suivi(),
        prix=prix,
        photo_url=None,
    )
    db.add(colis)
    await db.commit()

    result = await db.execute(
        select(Colis).options(selectinload(Colis.voyage)).where(Colis.id == colis.id)
    )
    return result.scalar_one()


# ─────────────────────────────────────────────────────────────────────────────
# Initier le paiement FedaPay des frais colis
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{colis_id}/initier-paiement")
async def initier_paiement_colis_endpoint(
    colis_id: UUID,
    payload: InitierPaiementPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    colis = await db.get(Colis, colis_id)
    if not colis:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    if colis.expediteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    if colis.statut != ColisStatut.EN_ATTENTE_PAIEMENT:
        raise HTTPException(status_code=409, detail="Paiement non attendu pour ce colis")
    if colis.paiement_expire_a and datetime.now(timezone.utc) > colis.paiement_expire_a:
        raise HTTPException(status_code=410, detail="Le délai de paiement a expiré")

    result = await initier_paiement_colis(colis, payload.telephone, db, current_user)
    await db.commit()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Vérifier le statut du paiement colis (polling)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{colis_id}/statut-paiement", response_model=ColisPaiementStatutRead)
async def statut_paiement_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    colis = await db.get(Colis, colis_id)
    if not colis:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    if colis.expediteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    statut = await verifier_et_confirmer_colis(colis, db)
    await db.commit()
    return ColisPaiementStatutRead(statut=statut, colis_statut=colis.statut)


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
# 3. Upload photo d'un colis
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{colis_id}/photo", response_model=ColisRead)
async def upload_colis_photo(
    request: Request,
    colis_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    colis = await _get_colis_with_voyage(colis_id, db)
    if colis.expediteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas l'expéditeur de ce colis")

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_MIME:
        raise HTTPException(status_code=415, detail="Format non supporté. Utilisez JPEG, PNG ou WebP.")

    data = await file.read()
    if len(data) > _MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 8 Mo)")

    ext = content_type.split("/")[-1].replace("jpeg", "jpg")
    filename = f"{_uuid.uuid4().hex}.{ext}"
    dest = _MEDIA_DIR / filename
    dest.write_bytes(data)

    base = str(request.base_url).rstrip("/")
    colis.photo_url = f"{base}/media/colis/{filename}"
    await db.commit()

    result = await db.execute(
        select(Colis).options(selectinload(Colis.voyage)).where(Colis.id == colis_id)
    )
    return result.scalar_one()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Détail d'un colis
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
# Annuler un colis (client ou chauffeur)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{colis_id}/annuler", response_model=ColisRead)
async def annuler_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    colis = await _get_colis_with_voyage(colis_id, db)

    annulable = {ColisStatut.EN_ATTENTE_PAIEMENT, ColisStatut.EN_ATTENTE}
    if colis.statut not in annulable:
        raise HTTPException(
            status_code=409,
            detail=f"Action impossible : statut actuel '{colis.statut}'",
        )

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
    await db.commit()
    return await _reload_colis(colis.id, db)


# ─────────────────────────────────────────────────────────────────────────────
# Confirmer un colis (chauffeur accepte)
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
    await db.commit()
    return await _reload_colis(colis.id, db)


# ─────────────────────────────────────────────────────────────────────────────
# Mettre en transit
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
    await db.commit()
    return await _reload_colis(colis.id, db)


# ─────────────────────────────────────────────────────────────────────────────
# Marquer comme livré
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
    await db.commit()
    return await _reload_colis(colis.id, db)
