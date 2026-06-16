"""Service de collecte des frais de mise en relation GoTaxi via FedaPay Mobile Money.

Flux réservation :
  POST /reservations              → crée en EN_ATTENTE_PAIEMENT, places bloquées
  POST /reservations/{id}/initier-paiement  → crée la transaction FedaPay + retourne payment_url
                                               (le client doit ouvrir ce lien pour choisir son
                                               opérateur Mobile Money et recevoir le push USSD)
  GET  /reservations/{id}/statut-paiement  → poll, confirme → EN_ATTENTE si payé

Flux colis :
  POST /colis                     → crée en EN_ATTENTE_PAIEMENT
  POST /colis/{id}/initier-paiement        → crée la transaction FedaPay + retourne payment_url
  GET  /colis/{id}/statut-paiement         → poll, confirme → EN_ATTENTE si payé

Tâche Celery (toutes les 60s) : annule les paiements expirés (>15 min).
"""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.reservation import Reservation, ReservationStatut
from app.models.colis import Colis, ColisStatut
from app.models.voyage import Voyage, VoyageStatut
from app.models.user import User
from app.models.transaction import Transaction, TransactionType, TransactionStatut, TransactionOperateur
from app.integrations.fedapay import fedapay
from app.core.logging import logger

FRAIS_RESERVATION_PAR_PLACE = 200   # FCFA par place réservée
FRAIS_COLIS_PLATEFORME = 100        # FCFA par demande de transport colis
PAIEMENT_EXPIRATION_MINUTES = 15


# ── Réservations ──────────────────────────────────────────────────────────────

async def initier_paiement_reservation(
    reservation: Reservation,
    telephone: str,
    db: AsyncSession,
    user: User,
) -> dict:
    """Crée la transaction FedaPay et retourne le lien de checkout à ouvrir."""
    tx_id = await fedapay.create_transaction(
        amount=reservation.frais_plateforme,
        description=f"Frais réservation GoTaxi #{reservation.code_confirmation}",
        phone=telephone,
        customer_firstname=user.prenom,
        customer_lastname=user.nom,
        customer_email=user.email,
    )
    token_data = await fedapay.get_payment_token(tx_id)
    reservation.fedapay_transaction_id = str(tx_id)
    await db.flush()
    logger.info("paiement_reservation_initie", reservation_id=str(reservation.id), tx_id=tx_id)
    return {
        "fedapay_tx_id": tx_id,
        "montant": reservation.frais_plateforme,
        "payment_url": token_data.get("payment_url") or token_data.get("url"),
    }


async def verifier_et_confirmer_reservation(
    reservation: Reservation,
    db: AsyncSession,
) -> str:
    """Poll FedaPay et confirme la réservation si le paiement est validé.

    Retourne : 'confirme' | 'en_attente' | 'echec' | 'expire' | 'non_initie'
    """
    if reservation.statut == ReservationStatut.EN_ATTENTE:
        return "confirme"

    if not reservation.fedapay_transaction_id:
        return "non_initie"

    if reservation.paiement_expire_a and datetime.now(timezone.utc) > reservation.paiement_expire_a:
        await _annuler_reservation(reservation, db, raison="expire")
        return "expire"

    statut_fp = await fedapay.get_transaction_status(int(reservation.fedapay_transaction_id))

    if fedapay.is_collection_success(statut_fp):
        await _valider_paiement_reservation(reservation, db)
        return "confirme"

    if fedapay.is_collection_failed(statut_fp):
        await _annuler_reservation(reservation, db, raison="echec")
        return "echec"

    return "en_attente"


async def _valider_paiement_reservation(reservation: Reservation, db: AsyncSession) -> None:
    reservation.statut = ReservationStatut.EN_ATTENTE
    tx = Transaction(
        type=TransactionType.FRAIS_RESERVATION,
        statut=TransactionStatut.REUSSI,
        operateur=TransactionOperateur.FEDAPAY,
        montant=reservation.frais_plateforme,
        user_id=reservation.client_id,
        reservation_id=reservation.id,
        reference_externe=reservation.fedapay_transaction_id,
    )
    db.add(tx)
    await db.flush()
    logger.info("paiement_reservation_confirme", reservation_id=str(reservation.id))


async def expirer_reservations_voyage(voyage: Voyage, db: AsyncSession) -> None:
    """Libère immédiatement les places bloquées par des réservations EN_ATTENTE_PAIEMENT
    expirées sur ce voyage, sans attendre le passage de la tâche Celery périodique
    (utile si Celery beat n'est pas démarré en dev, ou pour réagir plus vite)."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Reservation).where(
            Reservation.voyage_id == voyage.id,
            Reservation.statut == ReservationStatut.EN_ATTENTE_PAIEMENT,
            Reservation.paiement_expire_a <= now,
        )
    )
    for r in result.scalars():
        await _annuler_reservation(r, db, raison="expire")


async def _annuler_reservation(
    reservation: Reservation, db: AsyncSession, raison: str
) -> None:
    reservation.statut = ReservationStatut.ANNULEE
    voyage = await db.get(Voyage, reservation.voyage_id)
    if voyage and voyage.statut not in (VoyageStatut.TERMINE, VoyageStatut.ANNULE):
        voyage.nombre_places_restantes += reservation.nombre_places
        if voyage.statut == VoyageStatut.COMPLET and voyage.nombre_places_restantes > 0:
            voyage.statut = VoyageStatut.PUBLIE
    await db.flush()
    logger.info("reservation_annulee", reservation_id=str(reservation.id), raison=raison)


# ── Colis ─────────────────────────────────────────────────────────────────────

async def initier_paiement_colis(
    colis: Colis,
    telephone: str,
    db: AsyncSession,
    user: User,
) -> dict:
    """Crée la transaction FedaPay pour les frais colis et retourne le lien de checkout."""
    tx_id = await fedapay.create_transaction(
        amount=colis.frais_plateforme,
        description=f"Frais colis GoTaxi {colis.code_suivi}",
        phone=telephone,
        customer_firstname=user.prenom,
        customer_lastname=user.nom,
        customer_email=user.email,
    )
    token_data = await fedapay.get_payment_token(tx_id)
    colis.fedapay_transaction_id = str(tx_id)
    await db.flush()
    logger.info("paiement_colis_initie", colis_id=str(colis.id), tx_id=tx_id)
    return {
        "fedapay_tx_id": tx_id,
        "montant": colis.frais_plateforme,
        "payment_url": token_data.get("payment_url") or token_data.get("url"),
    }


async def verifier_et_confirmer_colis(
    colis: Colis,
    db: AsyncSession,
) -> str:
    """Poll FedaPay et confirme le colis si le paiement est validé."""
    if colis.statut == ColisStatut.EN_ATTENTE:
        return "confirme"

    if not colis.fedapay_transaction_id:
        return "non_initie"

    if colis.paiement_expire_a and datetime.now(timezone.utc) > colis.paiement_expire_a:
        colis.statut = ColisStatut.ANNULE
        await db.flush()
        return "expire"

    statut_fp = await fedapay.get_transaction_status(int(colis.fedapay_transaction_id))

    if fedapay.is_collection_success(statut_fp):
        colis.statut = ColisStatut.EN_ATTENTE
        tx = Transaction(
            type=TransactionType.FRAIS_COLIS,
            statut=TransactionStatut.REUSSI,
            operateur=TransactionOperateur.FEDAPAY,
            montant=colis.frais_plateforme,
            user_id=colis.expediteur_id,
            colis_id=colis.id,
            reference_externe=colis.fedapay_transaction_id,
        )
        db.add(tx)
        await db.flush()
        logger.info("paiement_colis_confirme", colis_id=str(colis.id))
        return "confirme"

    if fedapay.is_collection_failed(statut_fp):
        colis.statut = ColisStatut.ANNULE
        await db.flush()
        return "echec"

    return "en_attente"


# ── Nettoyage Celery (appelé depuis payment_tasks) ────────────────────────────

async def annuler_paiements_expires_async(db: AsyncSession) -> dict:
    """Annule toutes les réservations et colis EN_ATTENTE_PAIEMENT expirés."""
    now = datetime.now(timezone.utc)
    reservations_annulees = 0
    colis_annules = 0

    # Réservations expirées
    res = await db.execute(
        select(Reservation).where(
            Reservation.statut == ReservationStatut.EN_ATTENTE_PAIEMENT,
            Reservation.paiement_expire_a <= now,
        )
    )
    for r in res.scalars():
        await _annuler_reservation(r, db, raison="expire_celery")
        reservations_annulees += 1

    # Colis expirés
    res = await db.execute(
        select(Colis).where(
            Colis.statut == ColisStatut.EN_ATTENTE_PAIEMENT,
            Colis.paiement_expire_a <= now,
        )
    )
    for c in res.scalars():
        c.statut = ColisStatut.ANNULE
        colis_annules += 1

    await db.commit()
    return {"reservations_annulees": reservations_annulees, "colis_annules": colis_annules}
