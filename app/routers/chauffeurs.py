from uuid import UUID
from datetime import date, timezone, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.chauffeur import Chauffeur
from app.models.vehicule import Vehicule
from app.models.voyage import Voyage
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionType, TransactionStatut
from app.schemas.chauffeur import (
    ChauffeurRead, ChauffeurUpdate, ChauffeurPublic,
    VehiculeCreate, VehiculeUpdate, VehiculeRead, PositionUpdate,
    RevenusRead, ChauffeurStats,
)
from app.schemas.voyage import VoyageRead
from app.schemas.common import MessageResponse
from app.repositories.user_repository import UserRepository
from app.dependencies import get_current_user, require_role
from app.utils.validators import validate_image
from app.websockets.manager import manager
from app.exceptions import KYCNotValidatedException

router = APIRouter(prefix="/chauffeurs", tags=["Chauffeurs"])

require_chauffeur = require_role(UserRole.CHAUFFEUR)


async def _get_chauffeur_or_404(
    user: User,
    db: AsyncSession,
    load_vehicules: bool = False,
) -> Chauffeur:
    q = select(Chauffeur).where(Chauffeur.user_id == user.id)
    if load_vehicules:
        q = q.options(selectinload(Chauffeur.vehicules))
    result = await db.execute(q)
    chauffeur = result.scalar_one_or_none()
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Profil chauffeur introuvable")
    return chauffeur


@router.post("/me/setup", response_model=ChauffeurRead, status_code=201)
async def setup_chauffeur_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    result = await db.execute(select(Chauffeur).where(Chauffeur.user_id == current_user.id))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Profil chauffeur déjà initialisé")
    repo = UserRepository(db)
    chauffeur = await repo.init_chauffeur_profile(current_user.id)
    await db.commit()
    await db.refresh(chauffeur)
    return chauffeur


@router.get("/me", response_model=ChauffeurRead)
async def get_my_chauffeur_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    return await _get_chauffeur_or_404(current_user, db, load_vehicules=True)


@router.patch("/me", response_model=ChauffeurRead)
async def update_my_chauffeur_profile(
    payload: ChauffeurUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db, load_vehicules=True)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(chauffeur, field, value)
    await db.commit()
    await db.refresh(chauffeur)
    return chauffeur


@router.post("/me/documents", response_model=ChauffeurRead)
async def upload_documents(
    cin: UploadFile | None = File(None),
    permis: UploadFile | None = File(None),
    casier_judiciaire: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db, load_vehicules=True)
    from app.integrations.s3_storage import upload_file

    if cin is not None:
        content = await cin.read()
        try:
            validate_image(cin.content_type or "", len(content))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        chauffeur.cin_url = upload_file(content, "kyc/cin", cin.filename, cin.content_type or "image/jpeg")

    if permis is not None:
        content = await permis.read()
        try:
            validate_image(permis.content_type or "", len(content))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        chauffeur.permis_url = upload_file(content, "kyc/permis", permis.filename, permis.content_type or "image/jpeg")

    if casier_judiciaire is not None:
        content = await casier_judiciaire.read()
        try:
            validate_image(casier_judiciaire.content_type or "", len(content))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        chauffeur.casier_judiciaire_url = upload_file(
            content, "kyc/casier", casier_judiciaire.filename,
            casier_judiciaire.content_type or "image/jpeg",
        )

    await db.commit()
    await db.refresh(chauffeur)
    return chauffeur


@router.post("/me/online", response_model=MessageResponse)
async def go_online(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    if not chauffeur.kyc_valide:
        raise KYCNotValidatedException()
    chauffeur.en_ligne = True
    chauffeur.derniere_activite = date.today()
    await db.commit()
    if chauffeur.derniere_position_lat and chauffeur.derniere_position_lng:
        await manager.broadcast("admin:fleet", {
            "type": "driver_update",
            "driver": {
                "id": str(chauffeur.id),
                "user_id": str(chauffeur.user_id),
                "nom": current_user.nom,
                "prenom": current_user.prenom,
                "photo_url": current_user.photo_url,
                "lat": float(chauffeur.derniere_position_lat),
                "lng": float(chauffeur.derniere_position_lng),
                "vitesse": 0,
                "heading": 0,
                "status": "available",
                "voyage_id": None,
            },
        })
    return {"message": "Vous êtes maintenant en ligne"}


@router.post("/me/offline", response_model=MessageResponse)
async def go_offline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    chauffeur.en_ligne = False
    await db.commit()
    await manager.broadcast("admin:fleet", {
        "type": "driver_offline",
        "driver_id": str(chauffeur.id),
    })
    return {"message": "Vous êtes maintenant hors ligne"}


@router.post("/me/position", status_code=204)
async def update_position(
    payload: PositionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    chauffeur.derniere_position_lat = payload.lat
    chauffeur.derniere_position_lng = payload.lng
    chauffeur.derniere_activite = date.today()
    await db.commit()

    voyage_result = await db.execute(
        select(Voyage).where(
            Voyage.chauffeur_id == chauffeur.id,
            Voyage.statut == "EN_COURS",
        )
    )
    voyage = voyage_result.scalar_one_or_none()
    ts = datetime.now(timezone.utc).isoformat()

    if voyage:
        await manager.broadcast(
            f"tracking:voyage:{voyage.id}",
            {
                "type": "position_update",
                "voyage_id": str(voyage.id),
                "lat": payload.lat,
                "lng": payload.lng,
                "vitesse": payload.vitesse,
                "heading": payload.heading,
                "timestamp": ts,
            },
        )

    await manager.broadcast(
        "admin:fleet",
        {
            "type": "driver_update",
            "driver": {
                "id": str(chauffeur.id),
                "user_id": str(chauffeur.user_id),
                "nom": current_user.nom,
                "prenom": current_user.prenom,
                "photo_url": current_user.photo_url,
                "lat": payload.lat,
                "lng": payload.lng,
                "vitesse": payload.vitesse or 0,
                "heading": payload.heading or 0,
                "status": "in_trip" if voyage else "available",
                "voyage_id": str(voyage.id) if voyage else None,
            },
        },
    )


@router.get("/me/revenus", response_model=RevenusRead)
async def my_revenus(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)

    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == chauffeur.user_id))
    wallet = wallet_res.scalar_one_or_none()

    aujourd_hui = semaine = mois = 0

    if wallet:
        TZ_BENIN = timezone(timedelta(hours=1))
        now = datetime.now(TZ_BENIN)
        day_start   = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start  = day_start - timedelta(days=day_start.weekday())
        month_start = day_start.replace(day=1)

        # ECHEC = payout externe raté → wallet crédité en fallback → revenu réel
        statuts_valides = [TransactionStatut.REUSSI, TransactionStatut.EN_COURS, TransactionStatut.ECHEC]

        base = (
            select(func.coalesce(func.sum(Transaction.montant), 0))
            .where(
                Transaction.wallet_id == wallet.id,
                Transaction.type == TransactionType.REVERSEMENT,
                Transaction.statut.in_(statuts_valides),
            )
        )

        aujourd_hui = (await db.execute(base.where(Transaction.created_at >= day_start))).scalar() or 0
        semaine     = (await db.execute(base.where(Transaction.created_at >= week_start))).scalar() or 0
        mois        = (await db.execute(base.where(Transaction.created_at >= month_start))).scalar() or 0

    return RevenusRead(
        aujourd_hui=aujourd_hui,
        semaine=semaine,
        mois=mois,
        total=chauffeur.revenus_total,
    )


@router.get("/me/stats", response_model=ChauffeurStats)
async def my_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    return ChauffeurStats(
        nombre_trajets=chauffeur.nombre_trajets,
        revenus_total=chauffeur.revenus_total,
        note_moyenne=float(current_user.note_moyenne),
        nombre_avis=current_user.nombre_avis,
        en_ligne=chauffeur.en_ligne,
    )


@router.get("/me/vehicules", response_model=list[VehiculeRead])
async def my_vehicules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    result = await db.execute(
        select(Vehicule).where(Vehicule.chauffeur_id == chauffeur.id, Vehicule.actif == True)
    )
    return result.scalars().all()


@router.post("/me/vehicules", response_model=VehiculeRead, status_code=201)
async def add_vehicule(
    payload: VehiculeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    existing = await db.execute(
        select(Vehicule).where(Vehicule.immatriculation == payload.immatriculation)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Immatriculation déjà enregistrée")
    vehicule = Vehicule(**payload.model_dump(), chauffeur_id=chauffeur.id)
    db.add(vehicule)
    await db.commit()
    await db.refresh(vehicule)
    return vehicule


@router.post("/me/vehicules/{vehicule_id}/photo", response_model=VehiculeRead)
async def upload_vehicule_photo(
    vehicule_id: UUID,
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    vehicule = await db.get(Vehicule, vehicule_id)
    if not vehicule or vehicule.chauffeur_id != chauffeur.id:
        raise HTTPException(status_code=404, detail="Véhicule introuvable")
    content = await photo.read()
    try:
        validate_image(photo.content_type or "", len(content))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    from app.integrations.s3_storage import upload_file
    vehicule.photo_url = upload_file(content, "vehicules", photo.filename, photo.content_type or "image/jpeg")
    await db.commit()
    await db.refresh(vehicule)
    return vehicule


@router.patch("/me/vehicules/{vehicule_id}", response_model=VehiculeRead)
async def update_vehicule(
    vehicule_id: UUID,
    payload: VehiculeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    vehicule = await db.get(Vehicule, vehicule_id)
    if not vehicule or vehicule.chauffeur_id != chauffeur.id:
        raise HTTPException(status_code=404, detail="Véhicule introuvable")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(vehicule, field, value)
    await db.commit()
    await db.refresh(vehicule)
    return vehicule


@router.delete("/me/vehicules/{vehicule_id}", response_model=MessageResponse)
async def delete_vehicule(
    vehicule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    vehicule = await db.get(Vehicule, vehicule_id)
    if not vehicule or vehicule.chauffeur_id != chauffeur.id:
        raise HTTPException(status_code=404, detail="Véhicule introuvable")
    vehicule.actif = False
    await db.commit()
    return {"message": "Véhicule supprimé"}


@router.post("/me/vehicules/{vehicule_id}/documents", response_model=VehiculeRead)
async def upload_vehicule_documents(
    vehicule_id: UUID,
    assurance: UploadFile | None = File(None),
    assurance_expiration: str | None = Form(None),
    visite_technique: UploadFile | None = File(None),
    visite_technique_expiration: str | None = Form(None),
    titre: UploadFile | None = File(None),
    titre_expiration: str | None = Form(None),
    livret_bord: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    from datetime import date as date_type
    from app.integrations.s3_storage import upload_file

    chauffeur = await _get_chauffeur_or_404(current_user, db)
    vehicule = await db.get(Vehicule, vehicule_id)
    if not vehicule or vehicule.chauffeur_id != chauffeur.id:
        raise HTTPException(status_code=404, detail="Véhicule introuvable")

    async def _save_doc(file: UploadFile, folder: str) -> str:
        content = await file.read()
        try:
            validate_image(file.content_type or "", len(content))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return upload_file(content, folder, file.filename, file.content_type or "image/jpeg")

    if assurance:
        vehicule.assurance_url = await _save_doc(assurance, "vehicules/docs")
        if assurance_expiration:
            try:
                vehicule.assurance_expiration = date_type.fromisoformat(assurance_expiration)
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide pour assurance_expiration (YYYY-MM-DD)")
    elif assurance_expiration:
        try:
            vehicule.assurance_expiration = date_type.fromisoformat(assurance_expiration)
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide pour assurance_expiration (YYYY-MM-DD)")

    if visite_technique:
        vehicule.visite_technique_url = await _save_doc(visite_technique, "vehicules/docs")
        if visite_technique_expiration:
            try:
                vehicule.visite_technique_expiration = date_type.fromisoformat(visite_technique_expiration)
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide pour visite_technique_expiration (YYYY-MM-DD)")
    elif visite_technique_expiration:
        try:
            vehicule.visite_technique_expiration = date_type.fromisoformat(visite_technique_expiration)
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide pour visite_technique_expiration (YYYY-MM-DD)")

    if titre:
        vehicule.titre_url = await _save_doc(titre, "vehicules/docs")
        if titre_expiration:
            try:
                vehicule.titre_expiration = date_type.fromisoformat(titre_expiration)
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide pour titre_expiration (YYYY-MM-DD)")
    elif titre_expiration:
        try:
            vehicule.titre_expiration = date_type.fromisoformat(titre_expiration)
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide pour titre_expiration (YYYY-MM-DD)")

    if livret_bord:
        vehicule.livret_bord_url = await _save_doc(livret_bord, "vehicules/docs")

    # Réinitialise la validation admin dès qu'un nouveau doc est soumis
    vehicule.docs_vehicule_valides = False
    vehicule.docs_vehicule_valides_le = None

    await db.commit()
    await db.refresh(vehicule)
    return vehicule


@router.post("/me/vehicules/{vehicule_id}/photos-interieures", response_model=VehiculeRead)
async def upload_vehicule_interior_photo(
    vehicule_id: UUID,
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    vehicule = await db.get(Vehicule, vehicule_id)
    if not vehicule or vehicule.chauffeur_id != chauffeur.id:
        raise HTTPException(status_code=404, detail="Véhicule introuvable")
    if len(vehicule.photos_interieures or []) >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 photos intérieures autorisées")
    content = await photo.read()
    try:
        validate_image(photo.content_type or "", len(content))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    from app.integrations.s3_storage import upload_file
    url = upload_file(content, "vehicules/interieurs", photo.filename, photo.content_type or "image/jpeg")
    vehicule.photos_interieures = list(vehicule.photos_interieures or []) + [url]
    await db.commit()
    await db.refresh(vehicule)
    return vehicule


@router.delete("/me/vehicules/{vehicule_id}/photos-interieures/{index}", response_model=VehiculeRead)
async def delete_vehicule_interior_photo(
    vehicule_id: UUID,
    index: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_chauffeur),
):
    chauffeur = await _get_chauffeur_or_404(current_user, db)
    vehicule = await db.get(Vehicule, vehicule_id)
    if not vehicule or vehicule.chauffeur_id != chauffeur.id:
        raise HTTPException(status_code=404, detail="Véhicule introuvable")
    photos = list(vehicule.photos_interieures or [])
    if index < 0 or index >= len(photos):
        raise HTTPException(status_code=400, detail="Index invalide")
    photos.pop(index)
    vehicule.photos_interieures = photos
    await db.commit()
    await db.refresh(vehicule)
    return vehicule


@router.get("/{chauffeur_id}", response_model=ChauffeurPublic)
async def get_chauffeur_public(
    chauffeur_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Chauffeur)
        .options(selectinload(Chauffeur.user))
        .where(Chauffeur.id == chauffeur_id)
    )
    chauffeur = result.scalar_one_or_none()
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    user = chauffeur.user
    return ChauffeurPublic(
        id=chauffeur.id,
        nom=user.nom,
        prenom=user.prenom,
        photo_url=user.photo_url,
        note_moyenne=float(user.note_moyenne),
        nombre_avis=user.nombre_avis,
        nombre_trajets=chauffeur.nombre_trajets,
        en_ligne=chauffeur.en_ligne,
    )


@router.get("/{chauffeur_id}/voyages", response_model=list[VoyageRead])
async def get_chauffeur_voyages(
    chauffeur_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chauffeur = await db.get(Chauffeur, chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    result = await db.execute(
        select(Voyage)
        .where(Voyage.chauffeur_id == chauffeur_id, Voyage.statut != "ANNULE")
        .order_by(Voyage.date_depart.desc())
    )
    return result.scalars().all()