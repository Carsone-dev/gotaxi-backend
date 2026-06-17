import secrets
import string
from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update, Integer
from sqlalchemy.orm import selectinload, aliased
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus
from app.models.chauffeur import Chauffeur
from app.models.demande_chauffeur import DemandeInscriptionChauffeur, DemandeStatut
from app.models.wallet import Wallet
from app.models.voyage import Voyage, VoyageStatut
from app.models.colis import Colis, ColisStatut
from app.models.reservation import Reservation
from app.models.transaction import Transaction, TransactionType, TransactionStatut, TransactionOperateur
from app.models.avis import Avis
from app.models.audit import AuditLog
from app.dependencies import require_role
from app.schemas.user import UserRead
from app.schemas.chauffeur import ChauffeurRead, VehiculeRead
from app.schemas.voyage import VoyageRead, VoyageCreate
from app.models.vehicule import Vehicule
from app.models.tarif_trajet import TarifTrajet
from app.models.ville import Ville
from app.models.gare import Gare
from app.schemas.ville import VilleCreate, VilleUpdate, VilleRead
from app.schemas.gare import GareCreate, GareUpdate, GareRead
from app.schemas.colis import ColisRead
from app.schemas.reservation import ReservationRead
from app.schemas.avis import AvisRead
from app.schemas.wallet import TransactionRead
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.demande_chauffeur import (
    DemandeChauffeurRead,
    RejeterDemandeRequest,
    TraiterDemandeCredentials,
    TraiterDemandeResponse,
)
from app.models.payout_account import ComptePayoutChauffeur
from app.schemas.payout_account import ComptePayoutCreate, ComptePayoutRead
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/admin", tags=["Admin"])

require_admin = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_super_admin = require_role(UserRole.SUPER_ADMIN)


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
    rows = result.all()
    grand_total = sum(int(r.total) for r in rows) or 1
    return [
        {
            "operateur": r.operateur,
            "volume": int(r.total),
            "count": r.nb,
            "pct": round(int(r.total) / grand_total * 100, 1),
        }
        for r in rows
    ]


@router.get("/dashboard/benefices")
async def dashboard_benefices(
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Bénéfices de la plateforme : frais de mise en relation (réservations + colis),
    collectés exclusivement via le compte FedaPay unique de l'application."""
    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    async def _total_et_count(t: TransactionType) -> tuple[int, int]:
        row = (await db.execute(
            select(
                func.coalesce(func.sum(Transaction.montant), 0),
                func.count(Transaction.id),
            ).where(
                Transaction.type == t,
                Transaction.statut == TransactionStatut.REUSSI,
                Transaction.created_at >= since,
            )
        )).one()
        return int(row[0]), int(row[1])

    total_reservation, nb_reservation = await _total_et_count(TransactionType.FRAIS_RESERVATION)
    total_colis, nb_colis = await _total_et_count(TransactionType.FRAIS_COLIS)

    rows = (await db.execute(
        select(
            func.date(Transaction.created_at).label("jour"),
            Transaction.type,
            func.coalesce(func.sum(Transaction.montant), 0).label("total"),
        )
        .where(
            Transaction.type.in_([TransactionType.FRAIS_RESERVATION, TransactionType.FRAIS_COLIS]),
            Transaction.statut == TransactionStatut.REUSSI,
            Transaction.created_at >= since,
        )
        .group_by(func.date(Transaction.created_at), Transaction.type)
        .order_by(func.date(Transaction.created_at))
    )).all()

    par_jour: dict[str, dict[str, int]] = {}
    for r in rows:
        jour = str(r.jour)
        par_jour.setdefault(jour, {"frais_reservation": 0, "frais_colis": 0})
        if r.type == TransactionType.FRAIS_RESERVATION:
            par_jour[jour]["frais_reservation"] = int(r.total)
        else:
            par_jour[jour]["frais_colis"] = int(r.total)

    evolution = [
        {"date": jour, **vals, "total": vals["frais_reservation"] + vals["frais_colis"]}
        for jour, vals in sorted(par_jour.items())
    ]

    return {
        "total_frais_reservation": total_reservation,
        "total_frais_colis": total_colis,
        "total_general": total_reservation + total_colis,
        "nb_reservations_payees": nb_reservation,
        "nb_colis_payees": nb_colis,
        "evolution": evolution,
        "compte_collecte": "FedaPay — compte unique de la plateforme",
    }


# ─── Utilisateurs ────────────────────────────────────────────────────────────

@router.get("/users/stats")
async def users_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    rows = (await db.execute(
        select(User.statut, func.count(User.id).label("count"))
        .group_by(User.statut)
    )).all()
    rows_role = (await db.execute(
        select(User.role, func.count(User.id).label("count"))
        .group_by(User.role)
    )).all()
    return {
        "by_statut": [{"statut": r.statut.value, "count": r.count} for r in rows],
        "by_role": [{"role": r.role.value, "count": r.count} for r in rows_role],
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    statut: str | None = Query(None),
    role: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from sqlalchemy import or_
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
        filters.append(or_(
            User.nom.ilike(term), User.prenom.ilike(term), User.telephone.ilike(term)
        ))

    total = (await db.execute(
        select(func.count()).select_from(User).where(*filters)
    )).scalar() or 0

    result = await db.execute(
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()
    return {
        "items": [UserRead.model_validate(u).model_dump() for u in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, -(-total // size)),
    }


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


@router.post("/users/{user_id}/convert-to-chauffeur", response_model=MessageResponse)
async def convert_to_chauffeur(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if user.role != UserRole.CLIENT:
        raise HTTPException(status_code=400, detail="L'utilisateur doit être de rôle CLIENT")

    # Vérifier qu'aucun profil chauffeur n'existe déjà
    existing = (await db.execute(select(Chauffeur).where(Chauffeur.user_id == user_id))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Un profil chauffeur existe déjà pour cet utilisateur")

    user.role = UserRole.CHAUFFEUR
    user.statut = UserStatus.EN_ATTENTE_KYC

    chauffeur = Chauffeur(user_id=user.id)
    db.add(chauffeur)

    _log(db, current_user.id, "CONVERT_TO_CHAUFFEUR", "users", str(user_id))
    await db.commit()
    return {"message": "Compte converti en chauffeur. L'utilisateur peut soumettre ses documents KYC depuis l'application."}


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


# ─── Villes ──────────────────────────────────────────────────────────────────

@router.get("/villes", response_model=list[VilleRead])
async def admin_list_villes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Ville).order_by(Ville.nom))
    return result.scalars().all()


@router.post("/villes", response_model=VilleRead, status_code=201)
async def admin_create_ville(
    payload: VilleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = (await db.execute(select(Ville).where(Ville.nom == payload.nom))).scalar_one_or_none()
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Une ville avec ce nom existe déjà")
    ville = Ville(**payload.model_dump())
    db.add(ville)
    _log(db, current_user.id, "CREATE_VILLE", "ville", str(ville.id))
    await db.commit()
    await db.refresh(ville)
    return ville


@router.patch("/villes/{ville_id}", response_model=VilleRead)
async def admin_update_ville(
    ville_id: UUID,
    payload: VilleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from fastapi import HTTPException
    ville = await db.get(Ville, ville_id)
    if not ville:
        raise HTTPException(status_code=404, detail="Ville introuvable")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(ville, k, v)
    _log(db, current_user.id, "UPDATE_VILLE", "ville", str(ville_id))
    await db.commit()
    await db.refresh(ville)
    return ville


@router.delete("/villes/{ville_id}", response_model=MessageResponse)
async def admin_delete_ville(
    ville_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from fastapi import HTTPException
    ville = await db.get(Ville, ville_id)
    if not ville:
        raise HTTPException(status_code=404, detail="Ville introuvable")
    await db.delete(ville)
    _log(db, current_user.id, "DELETE_VILLE", "ville", str(ville_id))
    await db.commit()
    return {"message": "Ville supprimée"}


# ─── Gares ────────────────────────────────────────────────────────────────────

@router.get("/gares", response_model=list[GareRead])
async def admin_list_gares(
    ville_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if ville_id:
        filters.append(Gare.ville_id == ville_id)
    result = await db.execute(
        select(Gare)
        .options(selectinload(Gare.ville))
        .where(*filters)
        .order_by(Gare.nom)
    )
    return result.scalars().all()


@router.post("/gares", response_model=GareRead, status_code=201)
async def admin_create_gare(
    payload: GareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from fastapi import HTTPException
    ville = await db.get(Ville, payload.ville_id)
    if not ville:
        raise HTTPException(status_code=404, detail="Ville introuvable")
    gare = Gare(**payload.model_dump())
    db.add(gare)
    _log(db, current_user.id, "CREATE_GARE", "gare", str(gare.id))
    await db.commit()
    await db.refresh(gare)
    result = await db.execute(
        select(Gare).options(selectinload(Gare.ville)).where(Gare.id == gare.id)
    )
    return result.scalar_one()


@router.patch("/gares/{gare_id}", response_model=GareRead)
async def admin_update_gare(
    gare_id: UUID,
    payload: GareUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from fastapi import HTTPException
    result = await db.execute(
        select(Gare).options(selectinload(Gare.ville)).where(Gare.id == gare_id)
    )
    gare = result.scalar_one_or_none()
    if not gare:
        raise HTTPException(status_code=404, detail="Gare introuvable")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(gare, k, v)
    _log(db, current_user.id, "UPDATE_GARE", "gare", str(gare_id))
    await db.commit()
    await db.refresh(gare)
    result2 = await db.execute(
        select(Gare).options(selectinload(Gare.ville)).where(Gare.id == gare_id)
    )
    return result2.scalar_one()


@router.delete("/gares/{gare_id}", response_model=MessageResponse)
async def admin_delete_gare(
    gare_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from fastapi import HTTPException
    gare = await db.get(Gare, gare_id)
    if not gare:
        raise HTTPException(status_code=404, detail="Gare introuvable")
    await db.delete(gare)
    _log(db, current_user.id, "DELETE_GARE", "gare", str(gare_id))
    await db.commit()
    return {"message": "Gare supprimée"}


# ─── Voyages ─────────────────────────────────────────────────────────────────

@router.get("/voyages/stats")
async def voyages_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    rows = (await db.execute(
        select(Voyage.statut, func.count(Voyage.id).label("count"))
        .group_by(Voyage.statut)
    )).all()
    return {"by_statut": [{"statut": r.statut.value, "count": r.count} for r in rows]}


@router.get("/voyages")
async def list_voyages(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    statut: str | None = Query(None),
    chauffeur_id: str | None = Query(None),
    search: str | None = Query(None, description="Filtrer par ville départ ou arrivée"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if statut:
        try:
            filters.append(Voyage.statut == VoyageStatut(statut))
        except ValueError:
            pass
    if chauffeur_id:
        try:
            cid = UUID(chauffeur_id)
            # Accept either the chauffeur profile id or the user_id
            profile_id_row = await db.execute(
                select(Chauffeur.id).where(
                    (Chauffeur.id == cid) | (Chauffeur.user_id == cid)
                )
            )
            resolved = profile_id_row.scalar_one_or_none()
            if resolved:
                filters.append(Voyage.chauffeur_id == resolved)
            else:
                filters.append(Voyage.chauffeur_id == cid)
        except ValueError:
            pass
    if search and search.strip():
        term = f"%{search.strip()}%"
        from sqlalchemy import or_
        filters.append(or_(
            Voyage.ville_depart.ilike(term),
            Voyage.ville_arrivee.ilike(term),
        ))

    total = (await db.execute(
        select(func.count()).select_from(Voyage).where(*filters)
    )).scalar() or 0

    result = await db.execute(
        select(Voyage)
        .where(*filters)
        .order_by(Voyage.date_depart.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()

    return {
        "items": [VoyageRead.model_validate(v).model_dump() for v in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, -(-total // size)),
    }


@router.post("/voyages", response_model=VoyageRead, status_code=201)
async def admin_create_voyage(
    payload: VoyageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    vehicule = await db.get(Vehicule, payload.vehicule_id)
    if not vehicule or not vehicule.actif:
        raise HTTPException(status_code=404, detail="Véhicule introuvable ou inactif")

    tarif_result = await db.execute(
        select(TarifTrajet).where(
            TarifTrajet.ville_depart == payload.ville_depart,
            TarifTrajet.ville_arrivee == payload.ville_arrivee,
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
        chauffeur_id=vehicule.chauffeur_id,
        nombre_places_restantes=payload.nombre_places_total,
        date_arrivee_estimee=payload.date_depart,
    )
    db.add(voyage)
    _log(db, current_user.id, "ADMIN_CREATE_VOYAGE", "voyage", str(voyage.id))
    await db.commit()
    await db.refresh(voyage)
    return voyage


@router.get("/voyages/{voyage_id}")
async def get_voyage(
    voyage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    voyage_result = await db.execute(
        select(Voyage)
        .options(
            selectinload(Voyage.chauffeur).selectinload(Chauffeur.user),
            selectinload(Voyage.vehicule),
        )
        .where(Voyage.id == voyage_id)
    )
    voyage = voyage_result.scalar_one_or_none()
    if not voyage:
        raise HTTPException(status_code=404, detail="Voyage introuvable")
    reservations_result = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.client))
        .where(Reservation.voyage_id == voyage_id)
        .order_by(Reservation.created_at.desc())
    )
    reservations = reservations_result.scalars().all()
    chauffeur_user = (
        UserRead.model_validate(voyage.chauffeur.user)
        if voyage.chauffeur and voyage.chauffeur.user
        else None
    )
    vehicule = (
        VehiculeRead.model_validate(voyage.vehicule)
        if voyage.vehicule
        else None
    )
    return {
        "voyage": VoyageRead.model_validate(voyage),
        "reservations": [ReservationRead.model_validate(r) for r in reservations],
        "chauffeur": chauffeur_user,
        "vehicule": vehicule,
    }


# ─── Colis ───────────────────────────────────────────────────────────────────

@router.get("/colis", response_model=PaginatedResponse[ColisRead])
async def list_colis(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    statut: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if statut:
        try:
            filters.append(Colis.statut == ColisStatut(statut))
        except ValueError:
            pass

    total = (await db.execute(
        select(func.count()).select_from(Colis).where(*filters)
    )).scalar() or 0

    result = await db.execute(
        select(Colis)
        .options(selectinload(Colis.voyage))
        .where(*filters)
        .order_by(Colis.created_at.desc())
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


@router.get("/colis/{colis_id}")
async def get_colis(
    colis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Colis)
        .options(selectinload(Colis.voyage), selectinload(Colis.expediteur))
        .where(Colis.id == colis_id)
    )
    colis = result.scalar_one_or_none()
    if not colis:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    expediteur = UserRead.model_validate(colis.expediteur) if colis.expediteur else None
    return {
        "colis": ColisRead.model_validate(colis),
        "expediteur": expediteur,
    }


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

@router.get("/chauffeurs/stats")
async def chauffeurs_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    total     = (await db.execute(select(func.count()).select_from(Chauffeur))).scalar() or 0
    en_ligne  = (await db.execute(select(func.count()).select_from(Chauffeur).where(Chauffeur.en_ligne == True))).scalar() or 0
    kyc_ok    = (await db.execute(select(func.count()).select_from(Chauffeur).where(Chauffeur.kyc_valide == True))).scalar() or 0
    kyc_wait  = (await db.execute(select(func.count()).select_from(Chauffeur).where(Chauffeur.kyc_valide == False))).scalar() or 0
    return {"total": total, "en_ligne": en_ligne, "kyc_valide": kyc_ok, "kyc_attente": kyc_wait}


@router.get("/chauffeurs")
async def list_chauffeurs(
    kyc_valide: bool | None = Query(None),
    en_ligne: bool | None = Query(None),
    search: str | None = Query(None, description="Rechercher par nom, prénom ou téléphone"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from sqlalchemy import or_
    filters = []
    if kyc_valide is not None:
        filters.append(Chauffeur.kyc_valide == kyc_valide)
    if en_ligne is not None:
        filters.append(Chauffeur.en_ligne == en_ligne)
    if search and search.strip():
        term = f"%{search.strip()}%"
        user_ids = (
            select(User.id)
            .where(or_(User.nom.ilike(term), User.prenom.ilike(term), User.telephone.ilike(term)))
            .scalar_subquery()
        )
        filters.append(Chauffeur.user_id.in_(user_ids))

    total = (await db.execute(
        select(func.count()).select_from(Chauffeur).where(*filters)
    )).scalar() or 0

    result = await db.execute(
        select(Chauffeur)
        .options(selectinload(Chauffeur.vehicules), selectinload(Chauffeur.user))
        .where(*filters)
        .order_by(Chauffeur.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()

    def _serialize(c: Chauffeur) -> dict:
        d = ChauffeurRead.model_validate(c).model_dump()
        d["user"] = UserRead.model_validate(c.user).model_dump() if c.user else None
        return d

    return {
        "items": [_serialize(c) for c in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, -(-total // size)),
    }


@router.get("/chauffeurs/classement-avis")
async def classement_chauffeurs_avis(
    limit: int = Query(10, ge=1, le=50),
    ordre: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Classement des chauffeurs par note moyenne (meilleurs ou pires)."""
    order_fn = func.avg(Avis.note).desc() if ordre == "desc" else func.avg(Avis.note).asc()

    rows = (await db.execute(
        select(
            Avis.cible_id,
            func.avg(Avis.note).label("note_moy"),
            func.count(Avis.id).label("nb_avis"),
            func.sum(func.cast(Avis.signale, Integer)).label("nb_signales"),
        )
        .where(Avis.visible == True)
        .group_by(Avis.cible_id)
        .having(func.count(Avis.id) >= 1)
        .order_by(order_fn)
        .limit(limit)
    )).all()

    user_ids = [r.cible_id for r in rows]
    users_map: dict[UUID, User] = {}
    if user_ids:
        users_res = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u for u in users_res.scalars().all()}

    chauffeurs_map: dict[UUID, Chauffeur] = {}
    if user_ids:
        ch_res = await db.execute(select(Chauffeur).where(Chauffeur.user_id.in_(user_ids)))
        chauffeurs_map = {c.user_id: c for c in ch_res.scalars().all()}

    return [
        {
            "rang": i + 1,
            "chauffeur_id": str(chauffeurs_map[r.cible_id].id) if r.cible_id in chauffeurs_map else None,
            "user_id": str(r.cible_id),
            "nom": users_map[r.cible_id].nom if r.cible_id in users_map else None,
            "prenom": users_map[r.cible_id].prenom if r.cible_id in users_map else None,
            "photo_url": users_map[r.cible_id].photo_url if r.cible_id in users_map else None,
            "note_moyenne": round(float(r.note_moy), 2),
            "nb_avis": r.nb_avis,
            "nb_signales": int(r.nb_signales or 0),
        }
        for i, r in enumerate(rows)
    ]


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


# ─── Documents véhicules ──────────────────────────────────────────────────────

@router.get("/vehicules/docs-en-attente", response_model=list[VehiculeRead])
async def vehicules_docs_en_attente(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Véhicules ayant soumis au moins un document en attente de validation admin."""
    from sqlalchemy import or_
    result = await db.execute(
        select(Vehicule)
        .where(
            Vehicule.actif == True,
            Vehicule.docs_vehicule_valides == False,
            or_(
                Vehicule.assurance_url != None,
                Vehicule.visite_technique_url != None,
                Vehicule.titre_url != None,
                Vehicule.livret_bord_url != None,
            ),
        )
        .order_by(Vehicule.created_at.desc())
    )
    return result.scalars().all()


@router.post("/vehicules/{vehicule_id}/valider-docs", response_model=VehiculeRead)
async def valider_docs_vehicule(
    vehicule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Valide les documents réglementaires d'un véhicule."""
    vehicule = await db.get(Vehicule, vehicule_id)
    if not vehicule:
        raise HTTPException(status_code=404, detail="Véhicule introuvable")
    vehicule.docs_vehicule_valides = True
    vehicule.docs_vehicule_valides_le = date.today()
    _log(db, current_user.id, "VALIDER_DOCS_VEHICULE", "vehicules", str(vehicule_id))
    await db.commit()
    await db.refresh(vehicule)
    return vehicule


@router.post("/vehicules/{vehicule_id}/rejeter-docs", response_model=VehiculeRead)
async def rejeter_docs_vehicule(
    vehicule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Rejette les documents réglementaires d'un véhicule (réinitialise la validation)."""
    vehicule = await db.get(Vehicule, vehicule_id)
    if not vehicule:
        raise HTTPException(status_code=404, detail="Véhicule introuvable")
    vehicule.docs_vehicule_valides = False
    vehicule.docs_vehicule_valides_le = None
    _log(db, current_user.id, "REJETER_DOCS_VEHICULE", "vehicules", str(vehicule_id))
    await db.commit()
    await db.refresh(vehicule)
    return vehicule


# ─── Payout Account (admin) ──────────────────────────────────────────────────

@router.get("/chauffeurs/{chauffeur_id}/payout-account", response_model=ComptePayoutRead)
async def admin_get_payout_account(
    chauffeur_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    chauffeur = await db.get(Chauffeur, chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    result = await db.execute(
        select(ComptePayoutChauffeur).where(ComptePayoutChauffeur.chauffeur_id == chauffeur_id)
    )
    compte = result.scalar_one_or_none()
    if not compte:
        raise HTTPException(status_code=404, detail="Aucun compte payout configuré")
    return compte


@router.put("/chauffeurs/{chauffeur_id}/payout-account", response_model=ComptePayoutRead)
async def admin_upsert_payout_account(
    chauffeur_id: UUID,
    payload: ComptePayoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    chauffeur = await db.get(Chauffeur, chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    result = await db.execute(
        select(ComptePayoutChauffeur).where(ComptePayoutChauffeur.chauffeur_id == chauffeur_id)
    )
    compte = result.scalar_one_or_none()
    if compte:
        compte.operateur = payload.operateur
        compte.telephone = payload.telephone
        compte.actif = True
    else:
        compte = ComptePayoutChauffeur(
            chauffeur_id=chauffeur_id,
            operateur=payload.operateur,
            telephone=payload.telephone,
        )
        db.add(compte)
    try:
        await db.commit()
        await db.refresh(compte)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ce numéro est déjà utilisé par un autre chauffeur")
    _log(db, current_user.id, "UPSERT_PAYOUT_ACCOUNT", "comptes_payout_chauffeurs", str(chauffeur_id))
    return compte


@router.delete("/chauffeurs/{chauffeur_id}/payout-account", response_model=MessageResponse)
async def admin_delete_payout_account(
    chauffeur_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    chauffeur = await db.get(Chauffeur, chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    result = await db.execute(
        select(ComptePayoutChauffeur).where(ComptePayoutChauffeur.chauffeur_id == chauffeur_id)
    )
    compte = result.scalar_one_or_none()
    if not compte:
        raise HTTPException(status_code=404, detail="Aucun compte payout à supprimer")
    await db.delete(compte)
    _log(db, current_user.id, "DELETE_PAYOUT_ACCOUNT", "comptes_payout_chauffeurs", str(chauffeur_id))
    await db.commit()
    return {"message": "Compte payout supprimé"}


# ─── Avis / Modération ───────────────────────────────────────────────────────

@router.get("/avis")
async def list_avis(
    signale: bool | None = Query(None),
    visible: bool | None = Query(None),
    note: int | None = Query(None, ge=1, le=5),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if signale is not None:
        filters.append(Avis.signale == signale)
    if visible is not None:
        filters.append(Avis.visible == visible)
    if note is not None:
        filters.append(Avis.note == note)

    total = (await db.execute(
        select(func.count()).select_from(Avis).where(*filters)
    )).scalar() or 0

    result = await db.execute(
        select(Avis)
        .options(selectinload(Avis.auteur), selectinload(Avis.cible))
        .where(*filters)
        .order_by(Avis.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()

    def _ser(a: Avis) -> dict:
        return {
            **AvisRead.model_validate(a).model_dump(),
            "auteur": UserRead.model_validate(a.auteur).model_dump() if a.auteur else None,
            "cible":  UserRead.model_validate(a.cible).model_dump()  if a.cible  else None,
        }

    return {
        "items": [_ser(a) for a in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, -(-total // size)),
    }


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


@router.post("/avis/{avis_id}/restaurer", response_model=MessageResponse)
async def restaurer_avis(
    avis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    avis = await db.get(Avis, avis_id)
    if not avis:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    avis.visible = True
    avis.signale = False
    _log(db, current_user.id, "RESTAURER_AVIS", "avis", str(avis_id))
    await db.commit()
    return {"message": "Avis restauré"}


@router.get("/avis/stats")
async def avis_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Statistiques globales des avis : distribution des notes, signalés, masqués."""
    total = (await db.execute(select(func.count()).select_from(Avis))).scalar() or 0
    signales = (await db.execute(
        select(func.count()).select_from(Avis).where(Avis.signale == True)
    )).scalar() or 0
    masques = (await db.execute(
        select(func.count()).select_from(Avis).where(Avis.visible == False)
    )).scalar() or 0

    note_rows = (await db.execute(
        select(Avis.note, func.count(Avis.id).label("count"))
        .where(Avis.visible == True)
        .group_by(Avis.note)
        .order_by(Avis.note)
    )).all()

    note_moyenne_row = (await db.execute(
        select(func.avg(Avis.note)).where(Avis.visible == True)
    )).scalar()

    distribution = {str(i): 0 for i in range(1, 6)}
    for r in note_rows:
        distribution[str(r.note)] = r.count

    return {
        "total": total,
        "signales": signales,
        "masques": masques,
        "note_moyenne_globale": round(float(note_moyenne_row), 2) if note_moyenne_row else 0,
        "distribution_notes": distribution,
    }


@router.get("/chauffeurs/{chauffeur_id}/performance")
async def chauffeur_performance(
    chauffeur_id: UUID,
    period: str = Query("30d", pattern="^(7d|30d|90d|all)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Rapport de performance d'un chauffeur : notes, commentaires, évolution."""
    chauffeur = await db.get(Chauffeur, chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")

    user = await db.get(User, chauffeur.user_id)

    now = datetime.now(timezone.utc)
    since = None if period == "all" else now - timedelta(days={"7d": 7, "30d": 30, "90d": 90}[period])

    base_filter = [Avis.cible_id == chauffeur.user_id, Avis.visible == True]
    if since:
        base_filter.append(Avis.created_at >= since)

    avis_rows = (await db.execute(
        select(Avis).where(*base_filter).order_by(Avis.created_at.desc())
    )).scalars().all()

    total = len(avis_rows)
    note_moyenne = round(sum(a.note for a in avis_rows) / total, 2) if total else 0

    distribution = {str(i): 0 for i in range(1, 6)}
    for a in avis_rows:
        distribution[str(a.note)] += 1

    signales = sum(1 for a in avis_rows if a.signale)

    evolution_rows = (await db.execute(
        select(
            func.date(Avis.created_at).label("jour"),
            func.avg(Avis.note).label("note_moy"),
            func.count(Avis.id).label("nb"),
        )
        .where(*base_filter)
        .group_by(func.date(Avis.created_at))
        .order_by(func.date(Avis.created_at))
    )).all()

    nb_voyages_period_filter = [Voyage.chauffeur_id == chauffeur_id, Voyage.statut == VoyageStatut.TERMINE]
    if since:
        nb_voyages_period_filter.append(Voyage.date_depart >= since)
    nb_voyages = (await db.execute(
        select(func.count()).select_from(Voyage).where(*nb_voyages_period_filter)
    )).scalar() or 0

    taux_avis = round(total / nb_voyages * 100, 1) if nb_voyages > 0 else 0

    derniers_commentaires = [
        {
            "avis_id": str(a.id),
            "note": a.note,
            "commentaire": a.commentaire,
            "tags": a.tags,
            "voyage_id": str(a.voyage_id) if a.voyage_id else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in avis_rows[:10]
        if a.commentaire
    ]

    return {
        "chauffeur_id": str(chauffeur_id),
        "chauffeur_user_id": str(chauffeur.user_id),
        "nom": user.nom if user else None,
        "prenom": user.prenom if user else None,
        "photo_url": user.photo_url if user else None,
        "note_moyenne_globale": float(user.note_moyenne) if user else 0,
        "nombre_avis_total": user.nombre_avis if user else 0,
        "period": period,
        "stats_period": {
            "nb_avis": total,
            "note_moyenne": note_moyenne,
            "distribution_notes": distribution,
            "nb_signales": signales,
            "nb_voyages_termines": nb_voyages,
            "taux_avis_pct": taux_avis,
        },
        "evolution": [
            {"date": str(r.jour), "note_moyenne": round(float(r.note_moy), 2), "nb_avis": r.nb}
            for r in evolution_rows
        ],
        "derniers_commentaires": derniers_commentaires,
    }



# ─── Audit logs ──────────────────────────────────────────────────────────────

@router.get("/audit/stats")
async def audit_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = (await db.execute(select(func.count()).select_from(AuditLog))).scalar() or 0
    today = (await db.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= today_start)
    )).scalar() or 0
    unique_admins = (await db.execute(
        select(func.count(func.distinct(AuditLog.admin_id))).select_from(AuditLog)
    )).scalar() or 0
    action_rows = (await db.execute(
        select(AuditLog.action, func.count(AuditLog.id).label("count"))
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
    )).all()
    return {
        "total": total,
        "today": today,
        "unique_admins": unique_admins,
        "by_action": [{"action": r.action, "count": r.count} for r in action_rows],
    }


@router.get("/audit")
async def audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    entite: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if action:
        filters.append(AuditLog.action.ilike(f"%{action}%"))
    if entite:
        filters.append(AuditLog.entite == entite)

    base_q = select(AuditLog).where(*filters) if filters else select(AuditLog)
    total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar() or 0
    result = await db.execute(
        base_q
        .options(selectinload(AuditLog.admin))
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
                "admin_nom": log.admin.nom if log.admin else None,
                "admin_prenom": log.admin.prenom if log.admin else None,
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

@router.get("/reservations/stats")
async def reservations_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from app.models.reservation import ReservationStatut as RS
    rows = (await db.execute(
        select(Reservation.statut, func.count(Reservation.id).label("count"), func.sum(Reservation.prix_total).label("volume"))
        .group_by(Reservation.statut)
    )).all()
    volume_confirmees = sum(
        (r.volume or 0) for r in rows if r.statut in (RS.CONFIRMEE, RS.TERMINEE)
    )
    return {
        "by_statut": [{"statut": r.statut.value, "count": r.count, "volume": float(r.volume or 0)} for r in rows],
        "volume_confirmees": float(volume_confirmees),
    }


@router.get("/reservations", response_model=PaginatedResponse[ReservationRead])
async def list_reservations(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    statut: str | None = Query(None),
    voyage_id: str | None = Query(None),
    client_id: str | None = Query(None),
    search: str | None = Query(None, description="Recherche par code ou nom/prénom/téléphone client"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from app.models.reservation import ReservationStatut
    from sqlalchemy import or_
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
    if client_id:
        try:
            filters.append(Reservation.client_id == UUID(client_id))
        except ValueError:
            pass

    if search and search.strip():
        term = f"%{search.strip()}%"
        code_match = Reservation.code_confirmation.ilike(term)
        user_match = (
            select(User.id)
            .where(or_(
                User.nom.ilike(term),
                User.prenom.ilike(term),
                User.telephone.ilike(term),
            ))
            .scalar_subquery()
        )
        filters.append(or_(code_match, Reservation.client_id.in_(user_match)))

    base_q = select(Reservation).where(*filters)

    total = (await db.execute(
        select(func.count()).select_from(base_q.subquery())
    )).scalar() or 0

    result = await db.execute(
        base_q
        .options(selectinload(Reservation.client), selectinload(Reservation.voyage))
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


@router.get("/reservations/{reservation_id}")
async def get_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from app.models.reservation import ReservationStatut as RS
    result = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.client), selectinload(Reservation.voyage))
        .where(Reservation.id == reservation_id)
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    client_full = UserRead.model_validate(reservation.client) if reservation.client else None
    voyage_full = VoyageRead.model_validate(reservation.voyage) if reservation.voyage else None
    return {
        "reservation": ReservationRead.model_validate(reservation),
        "client_full": client_full,
        "voyage_full": voyage_full,
    }


@router.post("/reservations/{reservation_id}/cancel", response_model=MessageResponse)
async def cancel_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from app.models.reservation import ReservationStatut as RS
    reservation = await db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    if reservation.statut not in (RS.EN_ATTENTE, RS.CONFIRMEE):
        raise HTTPException(status_code=400, detail="Cette réservation ne peut pas être annulée")
    reservation.statut = RS.ANNULEE
    _log(db, current_user.id, "CANCEL_RESERVATION", "reservations", str(reservation_id))
    await db.commit()
    return {"message": "Réservation annulée"}


@router.post("/voyages/{voyage_id}/cancel", response_model=MessageResponse)
async def cancel_voyage_admin(
    voyage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from app.models.reservation import ReservationStatut as RS
    voyage = await db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail="Voyage introuvable")
    if voyage.statut not in (VoyageStatut.PUBLIE, VoyageStatut.COMPLET, VoyageStatut.EN_COURS):
        raise HTTPException(status_code=400, detail="Ce voyage ne peut pas être annulé")
    voyage.statut = VoyageStatut.ANNULE
    await db.execute(
        update(Reservation)
        .where(
            Reservation.voyage_id == voyage_id,
            Reservation.statut.in_([RS.EN_ATTENTE, RS.CONFIRMEE]),
        )
        .values(statut=RS.ANNULEE)
    )
    _log(db, current_user.id, "CANCEL_VOYAGE", "voyages", str(voyage_id))
    await db.commit()
    return {"message": "Voyage annulé — réservations associées annulées"}


# ─── Transactions ────────────────────────────────────────────────────────────

@router.get("/transactions/stats")
async def transactions_stats(
    type: str | None = Query(None),
    operateur: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filters = []
    if type:
        try: filters.append(Transaction.type == TransactionType(type))
        except ValueError: pass
    if operateur:
        try: filters.append(Transaction.operateur == TransactionOperateur(operateur))
        except ValueError: pass

    rows = (await db.execute(
        select(
            Transaction.statut,
            func.count(Transaction.id).label("count"),
            func.coalesce(func.sum(Transaction.montant), 0).label("volume"),
        )
        .where(*filters)
        .group_by(Transaction.statut)
    )).all()

    volume_total = (await db.execute(
        select(func.coalesce(func.sum(Transaction.montant), 0))
        .where(Transaction.statut == TransactionStatut.REUSSI, *filters)
    )).scalar() or 0

    return {
        "by_statut": [{"statut": r.statut.value, "count": r.count, "volume": int(r.volume)} for r in rows],
        "volume_reussi": int(volume_total),
    }


@router.get("/transactions")
async def list_transactions(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    statut: str | None = Query(None),
    type: str | None = Query(None),
    operateur: str | None = Query(None),
    search: str | None = Query(None, description="Recherche par nom/prénom/téléphone"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from app.models.wallet import Wallet as WalletModel
    from app.models.user import User as UserModel
    from sqlalchemy import or_

    filters = []
    if statut:
        try: filters.append(Transaction.statut == TransactionStatut(statut))
        except ValueError: pass
    if type:
        try: filters.append(Transaction.type == TransactionType(type))
        except ValueError: pass
    if operateur:
        try: filters.append(Transaction.operateur == TransactionOperateur(operateur))
        except ValueError: pass

    # Résolution de l'utilisateur :
    # - nouveau modèle (frais plateforme) → Transaction.user_id direct
    # - ancien modèle (wallet) → via wallet_id → wallet.user_id
    WalletUser = aliased(UserModel)
    DirectUser = aliased(UserModel)
    base_q = (
        select(Transaction)
        .join(WalletModel, Transaction.wallet_id == WalletModel.id, isouter=True)
        .join(WalletUser, WalletModel.user_id == WalletUser.id, isouter=True)
        .join(DirectUser, Transaction.user_id == DirectUser.id, isouter=True)
        .where(*filters)
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        base_q = base_q.where(
            or_(
                WalletUser.nom.ilike(term), WalletUser.prenom.ilike(term), WalletUser.telephone.ilike(term),
                DirectUser.nom.ilike(term), DirectUser.prenom.ilike(term), DirectUser.telephone.ilike(term),
            )
        )

    total = (await db.execute(
        select(func.count()).select_from(base_q.subquery())
    )).scalar() or 0

    result = await db.execute(
        base_q
        .options(
            selectinload(Transaction.wallet).selectinload(Wallet.user),
            selectinload(Transaction.user),
        )
        .order_by(Transaction.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()

    def _serialize(t: Transaction) -> dict:
        base = TransactionRead.model_validate(t).model_dump()
        u = t.user or (t.wallet.user if t.wallet else None)
        if u:
            base["user"] = {"id": str(u.id), "nom": u.nom, "prenom": u.prenom, "telephone": u.telephone, "role": u.role}
        else:
            base["user"] = None
        return base

    return {
        "items": [_serialize(t) for t in items],
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


# ─── Demandes d'inscription chauffeur ────────────────────────────────────────

def _gen_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("/demandes-chauffeur/stats")
async def demandes_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    rows = (await db.execute(
        select(DemandeInscriptionChauffeur.statut, func.count(DemandeInscriptionChauffeur.id).label("count"))
        .group_by(DemandeInscriptionChauffeur.statut)
    )).all()
    by_statut = {r.statut.value: r.count for r in rows}
    return {
        "nouvelle": by_statut.get("NOUVELLE", 0),
        "en_cours": by_statut.get("EN_COURS", 0),
        "traitee": by_statut.get("TRAITEE", 0),
        "rejetee": by_statut.get("REJETEE", 0),
        "total": sum(by_statut.values()),
    }


@router.get("/demandes-chauffeur", response_model=list[DemandeChauffeurRead])
async def list_demandes(
    statut: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from sqlalchemy import or_
    filters = []
    if statut:
        try:
            filters.append(DemandeInscriptionChauffeur.statut == DemandeStatut(statut))
        except ValueError:
            pass
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(or_(
            DemandeInscriptionChauffeur.nom.ilike(term),
            DemandeInscriptionChauffeur.prenom.ilike(term),
            DemandeInscriptionChauffeur.telephone.ilike(term),
            DemandeInscriptionChauffeur.ville.ilike(term),
        ))

    result = await db.execute(
        select(DemandeInscriptionChauffeur)
        .where(*filters)
        .order_by(DemandeInscriptionChauffeur.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()


@router.post("/demandes-chauffeur/{demande_id}/traiter", response_model=TraiterDemandeResponse)
async def traiter_demande(
    demande_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    demande = await db.get(DemandeInscriptionChauffeur, demande_id)
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if demande.statut == DemandeStatut.TRAITEE:
        raise HTTPException(status_code=400, detail="Cette demande a déjà été traitée")

    existing = (await db.execute(
        select(User).where(User.telephone == demande.telephone)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Un compte existe déjà pour le numéro {demande.telephone}",
        )

    password = _gen_password()
    user = User(
        telephone=demande.telephone,
        nom=demande.nom,
        prenom=demande.prenom,
        password_hash=hash_password(password),
        role=UserRole.CHAUFFEUR,
        statut=UserStatus.EN_ATTENTE_KYC,
    )
    db.add(user)
    await db.flush()

    chauffeur = Chauffeur(user_id=user.id)
    db.add(chauffeur)

    from app.models.wallet import Wallet
    wallet = Wallet(user_id=user.id)
    db.add(wallet)

    demande.statut = DemandeStatut.TRAITEE
    demande.user_id = user.id
    demande.traite_par_id = current_user.id
    demande.traite_le = datetime.now(timezone.utc)

    _log(db, current_user.id, "TRAITER_DEMANDE_CHAUFFEUR", "demandes_inscription_chauffeur", str(demande_id))
    await db.commit()

    return TraiterDemandeResponse(
        message=f"Compte chauffeur créé pour {demande.prenom} {demande.nom}",
        credentials=TraiterDemandeCredentials(
            telephone=demande.telephone,
            password=password,
            user_id=str(user.id),
        ),
    )


@router.post("/demandes-chauffeur/{demande_id}/rejeter", response_model=MessageResponse)
async def rejeter_demande(
    demande_id: UUID,
    payload: RejeterDemandeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    demande = await db.get(DemandeInscriptionChauffeur, demande_id)
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if demande.statut == DemandeStatut.TRAITEE:
        raise HTTPException(status_code=400, detail="Impossible de rejeter une demande déjà traitée")

    demande.statut = DemandeStatut.REJETEE
    demande.motif_rejet = payload.motif
    demande.traite_par_id = current_user.id
    demande.traite_le = datetime.now(timezone.utc)

    _log(db, current_user.id, "REJETER_DEMANDE_CHAUFFEUR", "demandes_inscription_chauffeur", str(demande_id))
    await db.commit()
    return MessageResponse(message="Demande rejetée")


# ─── Helper ──────────────────────────────────────────────────────────────────

def _log(db: AsyncSession, admin_id: UUID, action: str, entite: str, entite_id: str | None = None):
    db.add(AuditLog(admin_id=admin_id, action=action, entite=entite, entite_id=entite_id))
