"""Service de paiement direct aux chauffeurs.

Flux :
  1. Le client paie → wallet débité (PAIEMENT_VOYAGE / PAIEMENT_COLIS)
  2. A la fin du voyage ou à la livraison du colis → payer_chauffeur() est appelé
  3. Si le chauffeur a configuré un ComptePayoutChauffeur :
       → payout FedaPay / MTN / etc. envoyé immédiatement sur son téléphone
       → Transaction(REVERSEMENT, EN_COURS) créée sur son wallet GoTaxi pour traçabilité
  4. Sinon (pas de compte configuré) :
       → solde wallet GoTaxi du chauffeur crédité (retrait manuel ultérieur)
       → Transaction(REVERSEMENT, REUSSI) créée
"""
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.chauffeur import Chauffeur
from app.models.payout_account import ComptePayoutChauffeur
from app.models.transaction import Transaction, TransactionType, TransactionStatut, TransactionOperateur
from app.models.wallet import Wallet
from app.integrations.fedapay import fedapay, FedaPayError
from app.integrations.mtn_momo import mtn_momo, MTNMoMoError
from app.integrations.moov_money import moov_money, MoovMoneyError
from app.integrations.celtis import celtis, CeltisError


async def _get_chauffeur_wallet(chauffeur: Chauffeur, db: AsyncSession) -> Wallet | None:
    result = await db.execute(select(Wallet).where(Wallet.user_id == chauffeur.user_id))
    return result.scalar_one_or_none()


async def payer_chauffeur(
    chauffeur: Chauffeur,
    montant: int,
    db: AsyncSession,
    *,
    description: str = "Paiement GoTaxi",
) -> None:
    """Envoie le montant au chauffeur via son compte payout configuré.

    En cas d'échec du payout externe, fallback automatique vers le wallet GoTaxi.
    Enregistre toujours une Transaction REVERSEMENT pour la traçabilité.
    """
    if montant <= 0:
        return

    wallet = await _get_chauffeur_wallet(chauffeur, db)
    compte_result = await db.execute(
        select(ComptePayoutChauffeur).where(
            ComptePayoutChauffeur.chauffeur_id == chauffeur.id,
            ComptePayoutChauffeur.actif == True,
        )
    )
    compte = compte_result.scalar_one_or_none()

    # ── Pas de compte payout configuré : crédit wallet GoTaxi ────────────────
    if not compte:
        if wallet:
            wallet.solde += montant
            tx = Transaction(
                wallet_id=wallet.id,
                type=TransactionType.REVERSEMENT,
                statut=TransactionStatut.REUSSI,
                operateur=TransactionOperateur.WALLET,
                montant=montant,
            )
            db.add(tx)
        chauffeur.revenus_total += montant
        logger.info("payout_wallet_fallback", chauffeur_id=str(chauffeur.id), montant=montant)
        return

    # ── Compte payout configuré : payout direct ───────────────────────────────
    ext_ref: str | None = None
    statut = TransactionStatut.EN_COURS

    try:
        if compte.operateur == TransactionOperateur.FEDAPAY:
            payout_id = await fedapay.create_payout(
                amount=montant,
                phone=compte.telephone,
                customer_firstname=chauffeur.user.prenom if hasattr(chauffeur, "user") and chauffeur.user else "Chauffeur",
                customer_lastname=chauffeur.user.nom if hasattr(chauffeur, "user") and chauffeur.user else "GoTaxi",
            )
            await fedapay.send_payout(payout_id)
            ext_ref = str(payout_id)

        elif compte.operateur == TransactionOperateur.MTN_MOMO:
            ext_ref = await mtn_momo.transfer(montant, compte.telephone, str(uuid4()))

        elif compte.operateur == TransactionOperateur.MOOV_MONEY:
            # Moov Money : pas d'API disbursement directe → fallback wallet
            raise MoovMoneyError("Disbursement Moov non disponible via API — fallback wallet")

        elif compte.operateur == TransactionOperateur.CELTIS:
            ext_ref = await celtis.disburse(montant, compte.telephone, str(uuid4()))

        else:
            # Opérateur non supporté pour payout → fallback wallet
            raise ValueError(f"Opérateur payout non supporté : {compte.operateur}")

        chauffeur.revenus_total += montant
        logger.info(
            "payout_sent",
            chauffeur_id=str(chauffeur.id),
            operateur=compte.operateur,
            montant=montant,
            ref=ext_ref,
        )

    except (FedaPayError, MTNMoMoError, MoovMoneyError, CeltisError, ValueError) as e:
        logger.warning(
            "payout_failed_fallback_wallet",
            chauffeur_id=str(chauffeur.id),
            operateur=compte.operateur,
            error=str(e),
        )
        # Fallback : crédit wallet GoTaxi
        if wallet:
            wallet.solde += montant
        statut = TransactionStatut.ECHEC
        chauffeur.revenus_total += montant

    # Traçabilité dans le wallet GoTaxi (même si payout direct réussi)
    if wallet:
        tx = Transaction(
            wallet_id=wallet.id,
            type=TransactionType.REVERSEMENT,
            statut=statut,
            operateur=compte.operateur,
            montant=montant,
            reference_externe=ext_ref,
        )
        db.add(tx)


async def debiter_wallet_client(
    client_user_id: UUID,
    montant: int,
    type_transaction: TransactionType,
    db: AsyncSession,
    reference_id: str | None = None,
) -> None:
    """Débite le wallet du client pour un paiement voyage ou colis.

    Lève HTTP 402 si solde insuffisant (appelé avant db.commit).
    """
    from fastapi import HTTPException

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == client_user_id))
    wallet = wallet_result.scalar_one_or_none()

    if not wallet or not wallet.actif:
        raise HTTPException(status_code=402, detail="Wallet introuvable ou inactif")
    if wallet.solde < montant:
        raise HTTPException(status_code=402, detail="Solde insuffisant pour ce paiement")

    wallet.solde -= montant
    tx = Transaction(
        wallet_id=wallet.id,
        type=type_transaction,
        statut=TransactionStatut.REUSSI,
        operateur=TransactionOperateur.WALLET,
        montant=montant,
        reference_externe=reference_id,
    )
    db.add(tx)
