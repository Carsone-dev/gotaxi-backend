from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionType, TransactionStatut, TransactionOperateur
from app.schemas.wallet import (
    WalletRead, WalletPublic, RechargeInitiateRequest, RechargeInitiateResponse,
    WithdrawRequest, TransferRequest, TransactionRead,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.dependencies import get_current_user
from app.integrations.mtn_momo import mtn_momo, MTNMoMoError
from app.integrations.orange_money import orange_money, OrangeMoneyError
from app.integrations.moov_money import moov_money, MoovMoneyError
from app.integrations.celtis import celtis, CeltisError
from app.integrations.fedapay import fedapay, FedaPayError
from app.core.logging import logger
from fastapi import Query

router = APIRouter(prefix="/wallet", tags=["Wallet"])


async def _get_wallet_or_404(user: User, db: AsyncSession) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet introuvable")
    return wallet


@router.get("/me", response_model=WalletRead)
async def get_my_wallet(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_wallet_or_404(current_user, db)


@router.get("/me/activity", response_model=PaginatedResponse[TransactionRead])
async def wallet_activity(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wallet = await _get_wallet_or_404(current_user, db)
    result = await db.execute(
        select(Transaction)
        .where(Transaction.wallet_id == wallet.id)
        .order_by(Transaction.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()
    return PaginatedResponse(items=items, total=len(items), page=page, size=size, pages=1)


@router.post("/me/recharge/initiate", response_model=RechargeInitiateResponse)
async def initiate_recharge(
    payload: RechargeInitiateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wallet = await _get_wallet_or_404(current_user, db)
    transaction = Transaction(
        wallet_id=wallet.id,
        type=TransactionType.RECHARGE,
        statut=TransactionStatut.EN_ATTENTE,
        operateur=payload.operateur,
        montant=payload.montant,
    )
    db.add(transaction)
    await db.flush()

    try:
        if payload.operateur == TransactionOperateur.MTN_MOMO:
            ref = await mtn_momo.request_to_pay(payload.montant, payload.telephone, str(transaction.id))
            transaction.reference_externe = ref
            await db.commit()
            return {"message": f"Recharge MTN MoMo initiée. Confirmez le paiement USSD sur le {payload.telephone}."}

        elif payload.operateur == TransactionOperateur.ORANGE_MONEY:
            result = await orange_money.initiate_payment(payload.montant, payload.telephone, str(transaction.id))
            transaction.reference_externe = result.get("order_id") or str(transaction.id)
            await db.commit()
            payment_url = result.get("payment_url", "")
            msg = "Recharge Orange Money initiée."
            if payment_url:
                msg += f" Suivez le lien de paiement fourni."
            return {"message": msg}

        elif payload.operateur == TransactionOperateur.MOOV_MONEY:
            ref = await moov_money.collect(payload.montant, payload.telephone, str(transaction.id))
            transaction.reference_externe = ref
            await db.commit()
            return {"message": f"Recharge Moov Money initiée. Confirmez le paiement sur le {payload.telephone}."}

        elif payload.operateur == TransactionOperateur.CELTIS:
            ref = await celtis.collect(payload.montant, payload.telephone, str(transaction.id))
            transaction.reference_externe = ref
            await db.commit()
            return RechargeInitiateResponse(
                message=f"Recharge Celtis initiée. Confirmez le paiement USSD sur le {payload.telephone}."
            )

        elif payload.operateur == TransactionOperateur.FEDAPAY:
            tx_id = await fedapay.create_transaction(
                amount=payload.montant,
                description="Recharge wallet GoTaxi",
            )
            token_data = await fedapay.get_payment_token(tx_id)
            # On stocke l'id numérique FedaPay comme référence externe
            transaction.reference_externe = str(tx_id)
            await db.commit()
            payment_url = token_data.get("payment_url") or token_data.get("url", "")
            return RechargeInitiateResponse(
                message=f"Recharge FedaPay initiée. Ouvrez le lien de paiement et choisissez votre opérateur Mobile Money.",
                payment_url=payment_url,
            )

        else:
            raise HTTPException(status_code=400, detail="Opérateur non supporté")

    except (MTNMoMoError, OrangeMoneyError, MoovMoneyError, CeltisError, FedaPayError) as e:
        transaction.statut = TransactionStatut.ECHEC
        await db.commit()
        logger.error("recharge_initiate_failed", operateur=payload.operateur, error=str(e))
        raise HTTPException(status_code=502, detail=f"Erreur opérateur : {str(e)}")


@router.post("/me/recharge/confirm", response_model=WalletRead)
async def confirm_recharge(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from uuid import UUID
    wallet = await _get_wallet_or_404(current_user, db)
    transaction = await db.get(Transaction, UUID(transaction_id))
    if not transaction or transaction.wallet_id != wallet.id:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    if transaction.statut != TransactionStatut.EN_ATTENTE:
        raise HTTPException(status_code=400, detail="Transaction déjà traitée")
    if not transaction.reference_externe:
        raise HTTPException(status_code=400, detail="Aucune référence de paiement associée")

    try:
        if transaction.operateur == TransactionOperateur.MTN_MOMO:
            status_data = await mtn_momo.get_transaction_status(transaction.reference_externe)
            op_status = status_data.get("status", "")
            success_statuses = {"SUCCESSFUL"}
            failed_statuses = {"FAILED"}

        elif transaction.operateur == TransactionOperateur.ORANGE_MONEY:
            status_data = await orange_money.get_status(transaction.reference_externe)
            op_status = status_data.get("status", "")
            success_statuses = {"SUCCESS", "SUCCESSFUL"}
            failed_statuses = {"FAILED", "CANCELLED", "EXPIRED"}

        elif transaction.operateur == TransactionOperateur.MOOV_MONEY:
            status_data = await moov_money.get_status(transaction.reference_externe)
            op_status = status_data.get("status", "")
            success_statuses = {"SUCCESS", "SUCCESSFUL"}
            failed_statuses = {"FAILED", "CANCELLED"}

        elif transaction.operateur == TransactionOperateur.CELTIS:
            status_data = await celtis.get_status(transaction.reference_externe)
            op_status = status_data.get("status", "")
            success_statuses = {"SUCCESS", "SUCCESSFUL", "COMPLETED"}
            failed_statuses = {"FAILED", "CANCELLED", "EXPIRED", "REJECTED"}

        elif transaction.operateur == TransactionOperateur.FEDAPAY:
            op_status = await fedapay.get_transaction_status(int(transaction.reference_externe))
            success_statuses = {"approved", "transferred"}
            failed_statuses = {"declined", "cancelled", "refunded"}

        else:
            raise HTTPException(status_code=400, detail="Opérateur non supporté")

    except (MTNMoMoError, OrangeMoneyError, MoovMoneyError, CeltisError, FedaPayError) as e:
        logger.error("recharge_confirm_failed", tx_id=transaction_id, error=str(e))
        raise HTTPException(status_code=502, detail=f"Erreur vérification opérateur : {str(e)}")

    if op_status in success_statuses:
        transaction.statut = TransactionStatut.REUSSI
        wallet.solde += transaction.montant
        await db.commit()
        await db.refresh(wallet)
        return wallet
    elif op_status in failed_statuses:
        transaction.statut = TransactionStatut.ECHEC
        await db.commit()
        raise HTTPException(status_code=402, detail="Paiement refusé ou échoué")
    else:
        raise HTTPException(status_code=202, detail=f"Paiement en attente (statut: {op_status})")


@router.post("/me/withdraw", response_model=MessageResponse)
async def withdraw(
    payload: WithdrawRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wallet = await _get_wallet_or_404(current_user, db)
    if wallet.solde < payload.montant:
        raise HTTPException(status_code=402, detail="Solde insuffisant")

    wallet.solde -= payload.montant
    transaction = Transaction(
        wallet_id=wallet.id,
        type=TransactionType.REVERSEMENT,
        statut=TransactionStatut.EN_ATTENTE,
        operateur=payload.operateur,
        montant=payload.montant,
    )
    db.add(transaction)
    await db.flush()

    try:
        if payload.operateur == TransactionOperateur.MTN_MOMO:
            ref = await mtn_momo.transfer(payload.montant, payload.telephone, str(transaction.id))
            transaction.reference_externe = ref
            transaction.statut = TransactionStatut.EN_COURS
            await db.commit()
            return {"message": f"Retrait MTN MoMo de {payload.montant} XOF initié vers {payload.telephone}."}

        elif payload.operateur == TransactionOperateur.ORANGE_MONEY:
            # Orange Money disbursement non disponible via API directe — traitement manuel
            transaction.statut = TransactionStatut.EN_ATTENTE
            await db.commit()
            return {"message": f"Retrait Orange Money de {payload.montant} XOF en cours de traitement."}

        elif payload.operateur == TransactionOperateur.MOOV_MONEY:
            # Moov Money disbursement non disponible via API directe — traitement manuel
            transaction.statut = TransactionStatut.EN_ATTENTE
            await db.commit()
            return {"message": f"Retrait Moov Money de {payload.montant} XOF en cours de traitement."}

        elif payload.operateur == TransactionOperateur.CELTIS:
            ref = await celtis.disburse(payload.montant, payload.telephone, str(transaction.id))
            transaction.reference_externe = ref
            transaction.statut = TransactionStatut.EN_COURS
            await db.commit()
            return {"message": f"Retrait Celtis de {payload.montant} XOF initié vers {payload.telephone}."}

        elif payload.operateur == TransactionOperateur.FEDAPAY:
            payout_id = await fedapay.create_payout(payload.montant, payload.telephone)
            await fedapay.send_payout(payout_id)
            transaction.reference_externe = str(payout_id)
            transaction.statut = TransactionStatut.EN_COURS
            await db.commit()
            return {"message": f"Retrait FedaPay de {payload.montant} XOF initié vers {payload.telephone}."}

        else:
            wallet.solde += payload.montant
            transaction.statut = TransactionStatut.ANNULE
            await db.commit()
            raise HTTPException(status_code=400, detail="Opérateur non supporté")

    except (MTNMoMoError, CeltisError, FedaPayError) as e:
        wallet.solde += payload.montant
        transaction.statut = TransactionStatut.ECHEC
        await db.commit()
        logger.error("withdraw_failed", operateur=payload.operateur, error=str(e))
        raise HTTPException(status_code=502, detail=f"Erreur opérateur : {str(e)}")


@router.post("/me/transfer", response_model=MessageResponse)
async def transfer(
    payload: TransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.user import User as UserModel
    from sqlalchemy import select as sa_select
    wallet = await _get_wallet_or_404(current_user, db)
    if wallet.solde < payload.montant:
        raise HTTPException(status_code=402, detail="Solde insuffisant")

    dest_result = await db.execute(
        sa_select(UserModel).where(UserModel.telephone == payload.destinataire_telephone)
    )
    dest_user = dest_result.scalar_one_or_none()
    if not dest_user:
        raise HTTPException(status_code=404, detail="Destinataire introuvable")

    dest_wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == dest_user.id)
    )
    dest_wallet = dest_wallet_result.scalar_one_or_none()
    if not dest_wallet:
        raise HTTPException(status_code=404, detail="Wallet destinataire introuvable")

    wallet.solde -= payload.montant
    dest_wallet.solde += payload.montant

    tx_out = Transaction(
        wallet_id=wallet.id,
        type=TransactionType.REVERSEMENT,
        statut=TransactionStatut.REUSSI,
        operateur=TransactionOperateur.WALLET,
        montant=payload.montant,
    )
    tx_in = Transaction(
        wallet_id=dest_wallet.id,
        type=TransactionType.RECHARGE,
        statut=TransactionStatut.REUSSI,
        operateur=TransactionOperateur.WALLET,
        montant=payload.montant,
    )
    db.add_all([tx_out, tx_in])
    await db.commit()
    return {"message": f"Transfert de {payload.montant} XOF effectué vers {payload.destinataire_telephone}."}


@router.get("/search", response_model=WalletPublic)
async def search_wallet(
    telephone: str = Query(..., min_length=8, description="Numéro de téléphone GoTaxi à rechercher"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recherche le wallet d'un utilisateur par numéro de téléphone."""
    from app.models.user import User as UserModel
    from sqlalchemy import select as sa_select

    user_result = await db.execute(
        sa_select(UserModel).where(UserModel.telephone == telephone)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet introuvable")

    return WalletPublic(
        user_id=user.id,
        nom=user.nom,
        prenom=user.prenom,
        telephone=user.telephone,
        actif=wallet.actif,
    )