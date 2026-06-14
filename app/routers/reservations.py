from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.chauffeur import Chauffeur
from app.models.reservation import Reservation, ReservationStatut, ModalitePaiementReservation
from app.models.voyage import Voyage, VoyageStatut
from app.schemas.reservation import ReservationCreate, ReservationRead
from app.schemas.common import MessageResponse
from app.dependencies import get_current_user, require_role
from app.models.transaction import TransactionType
from app.services.payout import debiter_wallet_client
import secrets


_RESA_WITH_ALL = [
    selectinload(Reservation.voyage),
    selectinload(Reservation.client),
]


async def _get_reservation_full(reservation_id: UUID, db: AsyncSession) -> Reservation | None:
    result = await db.execute(
        select(Reservation)
        .options(*_RESA_WITH_ALL)
        .where(Reservation.id == reservation_id)
    )
    return result.scalar_one_or_none()

router = APIRouter(prefix="/reservations", tags=["Réservations"])


async def _get_chauffeur_id(user: User, db: AsyncSession) -> UUID | None:
    result = await db.execute(select(Chauffeur.id).where(Chauffeur.user_id == user.id))
    return result.scalar_one_or_none()


@router.post("", response_model=ReservationRead, status_code=201)
async def create_reservation(
    payload: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    voyage = await db.get(Voyage, payload.voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail="Voyage introuvable")
    if voyage.statut != VoyageStatut.PUBLIE:
        raise HTTPException(status_code=409, detail="Ce voyage n'accepte plus de réservations")
    if voyage.nombre_places_restantes < payload.nombre_places:
        raise HTTPException(status_code=409, detail="Places insuffisantes")

    chauffeur_id = await _get_chauffeur_id(current_user, db)
    if chauffeur_id and voyage.chauffeur_id == chauffeur_id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez pas réserver sur votre propre voyage")

    FRAIS_ESPECES_PAR_PLACE = 200

    prix_total = voyage.prix_par_place * payload.nombre_places
    montant_a_debiter = (
        FRAIS_ESPECES_PAR_PLACE * payload.nombre_places
        if payload.modalite_paiement == ModalitePaiementReservation.ESPECES
        else prix_total
    )

    reservation = Reservation(
        voyage_id=payload.voyage_id,
        client_id=current_user.id,
        nombre_places=payload.nombre_places,
        prix_total=prix_total,
        modalite_paiement=payload.modalite_paiement,
        code_confirmation=secrets.token_hex(3).upper(),
    )
    voyage.nombre_places_restantes -= payload.nombre_places
    if voyage.nombre_places_restantes == 0:
        voyage.statut = VoyageStatut.COMPLET

    db.add(reservation)
    await db.flush()

    await debiter_wallet_client(
        client_user_id=current_user.id,
        montant=montant_a_debiter,
        type_transaction=TransactionType.PAIEMENT_VOYAGE,
        db=db,
        reference_id=str(reservation.id),
    )

    await db.commit()

    return await _get_reservation_full(reservation.id, db)


@router.get("/me", response_model=list[ReservationRead])
async def my_reservations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Client : historique de ses réservations avec détails du voyage."""
    result = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.voyage))
        .where(Reservation.client_id == current_user.id)
        .order_by(Reservation.created_at.desc())
    )
    return result.scalars().all()


@router.get("/me/incoming", response_model=list[ReservationRead])
async def my_incoming_reservations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CHAUFFEUR)),
):
    """Chauffeur : demandes EN_ATTENTE et CONFIRMEE sur ses voyages — avec info client."""
    chauffeur_id = await _get_chauffeur_id(current_user, db)
    if not chauffeur_id:
        raise HTTPException(status_code=404, detail="Profil chauffeur introuvable")
    result = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.voyage), selectinload(Reservation.client))
        .join(Voyage, Reservation.voyage_id == Voyage.id)
        .where(
            Voyage.chauffeur_id == chauffeur_id,
            Reservation.statut.in_([ReservationStatut.EN_ATTENTE, ReservationStatut.CONFIRMEE]),
        )
        .order_by(Reservation.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{reservation_id}", response_model=ReservationRead)
async def get_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Détail d'une réservation : voyage embedded pour le client, client embedded pour le chauffeur."""
    reservation = await _get_reservation_full(reservation_id, db)
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable")

    is_client = reservation.client_id == current_user.id
    if not is_client:
        chauffeur_id = await _get_chauffeur_id(current_user, db)
        if not chauffeur_id or not reservation.voyage or reservation.voyage.chauffeur_id != chauffeur_id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")

    return reservation


@router.post("/{reservation_id}/accept", response_model=ReservationRead)
async def accept_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CHAUFFEUR)),
):
    """Chauffeur accepte → CONFIRMEE. Retourne la réservation avec info client."""
    chauffeur_id = await _get_chauffeur_id(current_user, db)
    reservation = await db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable")

    voyage = await db.get(Voyage, reservation.voyage_id)
    if not voyage or voyage.chauffeur_id != chauffeur_id:
        raise HTTPException(status_code=403, detail="Cette réservation ne concerne pas votre voyage")
    if reservation.statut != ReservationStatut.EN_ATTENTE:
        raise HTTPException(status_code=400, detail="Seule une réservation EN_ATTENTE peut être acceptée")

    reservation.statut = ReservationStatut.CONFIRMEE
    await db.commit()
    return await _get_reservation_full(reservation_id, db)


@router.post("/{reservation_id}/reject", response_model=ReservationRead)
async def reject_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CHAUFFEUR)),
):
    """Chauffeur refuse → REFUSEE. Places restituées au voyage."""
    chauffeur_id = await _get_chauffeur_id(current_user, db)
    reservation = await db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable")

    voyage = await db.get(Voyage, reservation.voyage_id)
    if not voyage or voyage.chauffeur_id != chauffeur_id:
        raise HTTPException(status_code=403, detail="Cette réservation ne concerne pas votre voyage")
    if reservation.statut != ReservationStatut.EN_ATTENTE:
        raise HTTPException(status_code=400, detail="Seule une réservation EN_ATTENTE peut être refusée")

    if voyage.statut in (VoyageStatut.PUBLIE, VoyageStatut.COMPLET):
        voyage.nombre_places_restantes += reservation.nombre_places
        if voyage.statut == VoyageStatut.COMPLET:
            voyage.statut = VoyageStatut.PUBLIE

    reservation.statut = ReservationStatut.REFUSEE
    await db.commit()
    return await _get_reservation_full(reservation_id, db)


@router.post("/{reservation_id}/cancel", response_model=ReservationRead)
async def cancel_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Client ou chauffeur annule → ANNULEE. Places restituées si voyage actif."""
    reservation = await db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable")

    is_client = reservation.client_id == current_user.id
    if not is_client:
        chauffeur_id = await _get_chauffeur_id(current_user, db)
        voyage_check = await db.get(Voyage, reservation.voyage_id)
        if not chauffeur_id or not voyage_check or voyage_check.chauffeur_id != chauffeur_id:
            raise HTTPException(status_code=403, detail="Non autorisé à annuler cette réservation")

    if reservation.statut not in (ReservationStatut.EN_ATTENTE, ReservationStatut.CONFIRMEE):
        raise HTTPException(status_code=400, detail="Réservation non annulable dans cet état")

    voyage = await db.get(Voyage, reservation.voyage_id)
    if voyage and voyage.statut not in (VoyageStatut.TERMINE, VoyageStatut.ANNULE):
        voyage.nombre_places_restantes += reservation.nombre_places
        if voyage.statut == VoyageStatut.COMPLET and voyage.nombre_places_restantes > 0:
            voyage.statut = VoyageStatut.PUBLIE

    reservation.statut = ReservationStatut.ANNULEE
    await db.commit()
    return await _get_reservation_full(reservation_id, db)