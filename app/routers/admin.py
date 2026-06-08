from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.chauffeur import Chauffeur
from app.models.voyage import Voyage, VoyageStatut
from app.models.colis import Colis, ColisStatut
from app.models.reservation import Reservation
from app.models.transaction import Transaction, TransactionType, TransactionStatut, TransactionOperateur
from app.models.avis import Avis
from app.models.audit import AuditLog
from app.dependencies import require_role
from app.schemas.user import UserRead
from app.schemas.chauffeur import ChauffeurRead
from app.schemas.voyage import VoyageRead
from app.schemas.colis import ColisRead
from app.schemas.reservation import ReservationRead
from app.schemas.avis import AvisRead
from app.schemas.wallet import TransactionRead
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/admin", tags=["Admin"])

require_admin = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)


# ─── Dashboard ───────────────────────────────────────────────────────────────

@router.get("/dashboard/overview")
async def dashboard_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    voyages_count = (await db.execute(select(func.count()).select_from(Voyage))).scalar() or 0
    colis_count = (await db.execute(select(func.count()).select_from(Colis))).scalar() or 0
    chauffeurs_count = (await db.execute(select(func.count()).select_from(Chauffeur))).scalar() or 0
    return {
        "total_utilisateurs": users_count,
        "total_voyages": voyages_count,
        "total_colis": colis_count,
        "total_chauffeurs": chauffeurs_count,
    }


@router.get("/dashboard/kpis")
async def dashboard_kpis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    new_users_week = (await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= week_start)
    )).scalar() or 0

    active_voyages = (await db.execute(
        select(func.count()).select_from(Voyage)
        .where(Voyage.statut.in_([VoyageStatut.PUBLIE, VoyageStatut.EN_COURS]))
    )).scalar() or 0

    revenus_mois = (await db.execute(
        select(func.coalesce(func.sum(Transaction.montant), 0))
        .where(
            Transaction.statut == TransactionStatut.REUSSI,
            Transaction.created_at >= month_start,
        )
    )).scalar() or 0

    colis_en_attente = (await db.execute(
        select(func.count()).select_from(Colis).where(Colis.statut == ColisStatut.EN_ATTENTE)
    )).scalar() or 0

    chauffeurs_en_ligne = (await db.execute(
        select(func.count()).select_from(Chauffeur).where(Chauffeur.en_ligne == True)
    )).scalar() or 0

    kyc_pending = (await db.execute(
        select(func.count()).select_from(Chauffeur).where(
            Chauffeur.kyc_valide == False,
            Chauffeur.cin_url != None,
        )
    )).scalar() or 0

    return {
        "total_utilisateurs": total_users,
        "nouveaux_utilisateurs_7j": new_users_week,
        "voyages_actifs": active_voyages,
        "revenus_30j_fcfa": int(revenus_mois),
        "colis_en_attente": colis_en_attente,
        "chauffeurs_en_ligne": chauffeurs_en_ligne,
        "kyc_en_attente": kyc_pending,
    }


@router.get("/dashboard/revenus")
async def dashboard_revenus(
    period: str = Query("7d", pattern="^(7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Transaction.created_at).label("jour"),
            func.coalesce(func.sum(Transaction.montant), 0).label("total"),
            func.count(Transaction.id).label("nb_transactions"),
        )
        .where(
            Transaction.statut == TransactionStatut.REUSSI,
            Transaction.created_at >= since,
        )
        .group_by(func.date(Transaction.created_at))
        .order_by(func.date(Transaction.created_at))
    )
    rows = result.all()
    return {
        "period": period,
        "data": [
            {"date": str(r.jour), "revenus": int(r.total), "transactions": r.nb_transactions}
            for r in rows
        ],
    }


@router.get("/dashboard/top-trajets")
async def dashboard_top_trajets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(
            Voyage.ville_depart,
            Voyage.ville_arrivee,
            func.count(Voyage.id).label("nb_voyages"),
        )
        .group_by(Voyage.ville_depart, Voyage.ville_arrivee)
        .order_by(func.count(Voyage.id).desc())
        .limit(10)
    )
    return [
        {"ville_depart": r.ville_depart, "ville_arrivee": r.ville_arrivee, "nb_voyages": r.nb_voyages}
        for r in result.all()
    ]


@router.get("/dashboard/activity-feed")
async def dashboard_activity_feed(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    events = []

    recent_users = (await db.execute(
        select(User).order_by(User.created_at.desc()).limit(5)
    )).scalars().all()
    for u in recent_users:
        events.append({
            "type": "NEW_USER",
            "message": f"Nouvel utilisateur : {u.prenom} {u.nom}",
            "created_at": u.created_at.isoformat(),
        })

    recent_voyages = (await db.execute(
        select(Voyage).order_by(Voyage.created_at.desc()).limit(5)
    )).scalars().all()
    for v in recent_voyages:
        events.append({
            "type": "NEW_VOYAGE",
            "message": f"Nouveau voyage : {v.ville_depart} → {v.ville_arrivee}",
            "created_at": v.created_at.isoformat(),
        })

    recent_colis = (await db.execute(
        select(Colis).order_by(Colis.created_at.desc()).limit(5)
    )).scalars().all()
    for c in recent_colis:
        events.append({
            "type": "NEW_COLIS",
            "message": f"Nouveau colis : {c.ville_depart} → {c.ville_arrivee} ({c.code_suivi})",
            "created_at": c.created_at.isoformat(),
        })

    events.sort(key=lambda x: x["created_at"], reverse=True)
    return events[:20]


@router.get("/dashboard/momo-stats")
async def dashboard_momo_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(
            Transaction.operateur,
            func.count(Transaction.id).label("nb"),
            func.coalesce(func.sum(Transaction.montant), 0).label("total"),
        )
        .where(Transaction.statut == TransactionStatut.REUSSI)
        .group_by(Transaction.operateur)
    )
    return [
        {"operateur": r.operateur, "nb_transactions": r.nb, "total_fcfa": int(r.total)}
        for r in result.all()
    ]


# ─── Utilisateurs ────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserRead])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    statut: str | None = Query(None),
    role: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if statut:
        try:
            filters.append(User.statut == UserStatus(statut))
        except ValueError:
            pass
    if role:
        try:
            filters.append(User.role == UserRole(role))
        except ValueError:
            pass
    if search:
        term = f"%{search}%"
        filters.append(
            User.nom.ilike(term) | User.prenom.ilike(term) | User.telephone.ilike(term)
        )

    result = await db.execute(
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


@router.post("/users/{user_id}/suspend", response_model=MessageResponse)
async def suspend_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.statut = UserStatus.SUSPENDU
    _log(db, current_user.id, "SUSPEND_USER", "users", str(user_id))
    await db.commit()
    return {"message": "Utilisateur suspendu"}


@router.post("/users/{user_id}/activate", response_model=MessageResponse)
async def activate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.statut = UserStatus.ACTIF
    _log(db, current_user.id, "ACTIVATE_USER", "users", str(user_id))
    await db.commit()
    return {"message": "Utilisateur activé"}


@router.post("/users/{user_id}/validate-kyc", response_model=MessageResponse)
async def validate_kyc_by_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Chauffeur).where(Chauffeur.user_id == user_id))
    chauffeur = result.scalar_one_or_none()
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable pour cet utilisateur")
    chauffeur.kyc_valide = True
    chauffeur.kyc_valide_le = date.today()
    _log(db, current_user.id, "VALIDATE_KYC", "chauffeurs", str(chauffeur.id))
    await db.commit()
    return {"message": "KYC validé"}


# ─── Voyages ─────────────────────────────────────────────────────────────────

@router.get("/voyages", response_model=list[VoyageRead])
async def list_voyages(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    statut: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if statut:
        try:
            filters.append(Voyage.statut == VoyageStatut(statut))
        except ValueError:
            pass
    result = await db.execute(
        select(Voyage)
        .where(*filters)
        .order_by(Voyage.date_depart.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()


@router.get("/voyages/{voyage_id}")
async def get_voyage(
    voyage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    voyage = await db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail="Voyage introuvable")
    reservations_result = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.client))
        .where(Reservation.voyage_id == voyage_id)
        .order_by(Reservation.created_at.desc())
    )
    reservations = reservations_result.scalars().all()
    return {
        "voyage": VoyageRead.model_validate(voyage),
        "reservations": [ReservationRead.model_validate(r) for r in reservations],
    }


# ─── Colis ───────────────────────────────────────────────────────────────────

@router.get("/colis/pending", response_model=list[ColisRead])
async def pending_colis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Colis)
        .options(selectinload(Colis.voyage))
        .where(Colis.statut == ColisStatut.EN_ATTENTE)
        .order_by(Colis.created_at.desc())
    )
    return result.scalars().all()


@router.get("/colis/in-transit", response_model=list[ColisRead])
async def in_transit_colis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Colis)
        .options(selectinload(Colis.voyage))
        .where(Colis.statut.in_([ColisStatut.CONFIRME, ColisStatut.EN_TRANSIT]))
        .order_by(Colis.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/colis/{colis_id}", response_model=ColisRead)
async def get_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Colis).options(selectinload(Colis.voyage)).where(Colis.id == colis_id)
    )
    colis = result.scalar_one_or_none()
    if not colis:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    return colis


@router.post("/colis/{colis_id}/validate", response_model=MessageResponse)
async def validate_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    colis = await db.get(Colis, colis_id)
    if not colis:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    colis.statut = ColisStatut.CONFIRME
    _log(db, current_user.id, "VALIDATE_COLIS", "colis", str(colis_id))
    await db.commit()
    return {"message": "Colis validé"}


@router.post("/colis/{colis_id}/reject", response_model=MessageResponse)
async def reject_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    colis = await db.get(Colis, colis_id)
    if not colis:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    colis.statut = ColisStatut.ANNULE
    _log(db, current_user.id, "REJECT_COLIS", "colis", str(colis_id))
    await db.commit()
    return {"message": "Colis rejeté"}


# ─── Chauffeurs / KYC ────────────────────────────────────────────────────────

@router.get("/chauffeurs", response_model=list[ChauffeurRead])
async def list_chauffeurs(
    kyc_valide: bool | None = Query(None),
    en_ligne: bool | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if kyc_valide is not None:
        filters.append(Chauffeur.kyc_valide == kyc_valide)
    if en_ligne is not None:
        filters.append(Chauffeur.en_ligne == en_ligne)
    result = await db.execute(
        select(Chauffeur)
        .options(selectinload(Chauffeur.vehicules))
        .where(*filters)
        .order_by(Chauffeur.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()


@router.get("/chauffeurs/{user_id}")
async def get_chauffeur(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    chauffeur_result = await db.execute(
        select(Chauffeur)
        .options(selectinload(Chauffeur.vehicules))
        .where(Chauffeur.user_id == user_id)
    )
    chauffeur = chauffeur_result.scalar_one_or_none()
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    user = await db.get(User, user_id)
    return {
        "user": UserRead.model_validate(user),
        "chauffeur": ChauffeurRead.model_validate(chauffeur),
    }


@router.post("/chauffeurs/{chauffeur_id}/validate-kyc", response_model=MessageResponse)
async def validate_kyc(
    chauffeur_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    chauffeur = await db.get(Chauffeur, chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    chauffeur.kyc_valide = True
    chauffeur.kyc_valide_le = date.today()
    _log(db, current_user.id, "VALIDATE_KYC", "chauffeurs", str(chauffeur_id))
    await db.commit()
    return {"message": "KYC validé"}


@router.post("/chauffeurs/{chauffeur_id}/reject-kyc", response_model=MessageResponse)
async def reject_kyc(
    chauffeur_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    chauffeur = await db.get(Chauffeur, chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    chauffeur.kyc_valide = False
    chauffeur.kyc_valide_le = None
    _log(db, current_user.id, "REJECT_KYC", "chauffeurs", str(chauffeur_id))
    await db.commit()
    return {"message": "KYC rejeté"}


# ─── Avis / Modération ───────────────────────────────────────────────────────

@router.get("/avis", response_model=list[AvisRead])
async def list_avis(
    signale: bool | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if signale is not None:
        filters.append(Avis.signale == signale)
    result = await db.execute(
        select(Avis)
        .where(*filters)
        .order_by(Avis.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()


@router.post("/avis/{avis_id}/masquer", response_model=MessageResponse)
async def masquer_avis(
    avis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    avis = await db.get(Avis, avis_id)
    if not avis:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    avis.visible = False
    _log(db, current_user.id, "MASQUER_AVIS", "avis", str(avis_id))
    await db.commit()
    return {"message": "Avis masqué"}


# ─── Audit logs ──────────────────────────────────────────────────────────────

@router.get("/audit")
async def audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    total = (await db.execute(select(func.count()).select_from(AuditLog))).scalar() or 0
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": str(log.id),
                "action": log.action,
                "admin_id": str(log.admin_id),
                "target_type": log.entite,
                "target_id": log.entite_id,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in items
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, -(-total // size)),
    }


# ─── Réservations ────────────────────────────────────────────────────────────

@router.get("/reservations", response_model=PaginatedResponse[ReservationRead])
async def list_reservations(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    statut: str | None = Query(None),
    voyage_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from app.models.reservation import ReservationStatut
    filters = []
    if statut:
        try:
            filters.append(Reservation.statut == ReservationStatut(statut))
        except ValueError:
            pass
    if voyage_id:
        try:
            filters.append(Reservation.voyage_id == UUID(voyage_id))
        except ValueError:
            pass

    total = (await db.execute(
        select(func.count()).select_from(Reservation).where(*filters)
    )).scalar() or 0

    result = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.client), selectinload(Reservation.voyage))
        .where(*filters)
        .order_by(Reservation.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return PaginatedResponse(
        items=result.scalars().all(),
        total=total,
        page=page,
        size=size,
        pages=max(1, -(-total // size)),
    )


# ─── Transactions ────────────────────────────────────────────────────────────

@router.get("/transactions")
async def list_transactions(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    statut: str | None = Query(None),
    type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if statut:
        try:
            filters.append(Transaction.statut == TransactionStatut(statut))
        except ValueError:
            pass
    if type:
        try:
            filters.append(Transaction.type == TransactionType(type))
        except ValueError:
            pass

    total = (await db.execute(
        select(func.count()).select_from(Transaction).where(*filters)
    )).scalar() or 0

    result = await db.execute(
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()
    return {
        "items": [TransactionRead.model_validate(t) for t in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, -(-total // size)),
    }


# ─── Fleet snapshot REST (fallback polling si WS non connecté) ───────────────

@router.get("/fleet")
async def fleet_snapshot(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from sqlalchemy.orm import selectinload as _sil
    result = await db.execute(
        select(Chauffeur)
        .options(_sil(Chauffeur.user))
        .where(
            Chauffeur.en_ligne == True,
            Chauffeur.derniere_position_lat != None,
            Chauffeur.derniere_position_lng != None,
        )
    )
    chauffeurs = result.scalars().all()

    voyages_result = await db.execute(
        select(Voyage).where(Voyage.statut == VoyageStatut.EN_COURS)
    )
    active_voyages = {v.chauffeur_id: v for v in voyages_result.scalars().all()}

    drivers = []
    trips = []
    for c in chauffeurs:
        voyage = active_voyages.get(c.id)
        drivers.append({
            "id": str(c.id),
            "user_id": str(c.user_id),
            "nom": c.user.nom,
            "prenom": c.user.prenom,
            "photo_url": c.user.photo_url,
            "lat": float(c.derniere_position_lat),
            "lng": float(c.derniere_position_lng),
            "vitesse": 0,
            "heading": 0,
            "status": "in_trip" if voyage else "available",
            "voyage_id": str(voyage.id) if voyage else None,
        })
        if voyage:
            trips.append({
                "id": str(voyage.id),
                "chauffeur_id": str(c.id),
                "ville_depart": voyage.ville_depart,
                "ville_arrivee": voyage.ville_arrivee,
                "date_depart": voyage.date_depart.isoformat(),
                "passagers": 0,
                "statut": voyage.statut,
            })

    return {"drivers": drivers, "trips": trips}


# ─── Helper ──────────────────────────────────────────────────────────────────

def _log(db: AsyncSession, admin_id: UUID, action: str, entite: str, entite_id: str | None = None):
    db.add(AuditLog(admin_id=admin_id, action=action, entite=entite, entite_id=entite_id))
