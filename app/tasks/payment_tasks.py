import asyncio
from app.tasks.celery_app import celery_app
from app.core.logging import logger


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@celery_app.task
def check_pending_payments():
    """Vérifie le statut des paiements en attente (tous opérateurs) et met à jour les transactions."""
    async def _check():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from sqlalchemy import select
        from app.config import get_settings
        from app.models.transaction import Transaction, TransactionStatut, TransactionOperateur
        from app.models.wallet import Wallet
        from app.integrations.mtn_momo import mtn_momo, MTNMoMoError
        from app.integrations.orange_money import orange_money, OrangeMoneyError
        from app.integrations.moov_money import moov_money, MoovMoneyError

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with SessionLocal() as db:
            result = await db.execute(
                select(Transaction).where(
                    Transaction.statut == TransactionStatut.EN_ATTENTE,
                    Transaction.operateur.in_([
                        TransactionOperateur.MTN_MOMO,
                        TransactionOperateur.ORANGE_MONEY,
                        TransactionOperateur.MOOV_MONEY,
                    ]),
                    Transaction.reference_externe.isnot(None),
                )
            )
            pending = result.scalars().all()
            updated = 0

            for tx in pending:
                try:
                    if tx.operateur == TransactionOperateur.MTN_MOMO:
                        status_data = await mtn_momo.get_transaction_status(tx.reference_externe)
                        op_status = status_data.get("status", "")
                        success = op_status == "SUCCESSFUL"
                        failed = op_status == "FAILED"

                    elif tx.operateur == TransactionOperateur.ORANGE_MONEY:
                        status_data = await orange_money.get_status(tx.reference_externe)
                        op_status = status_data.get("status", "")
                        success = op_status in ("SUCCESS", "SUCCESSFUL")
                        failed = op_status in ("FAILED", "CANCELLED", "EXPIRED")

                    elif tx.operateur == TransactionOperateur.MOOV_MONEY:
                        status_data = await moov_money.get_status(tx.reference_externe)
                        op_status = status_data.get("status", "")
                        success = op_status in ("SUCCESS", "SUCCESSFUL")
                        failed = op_status in ("FAILED", "CANCELLED")

                    else:
                        continue

                    if success:
                        tx.statut = TransactionStatut.REUSSI
                        wallet = await db.get(Wallet, tx.wallet_id)
                        if wallet:
                            wallet.solde += tx.montant
                        updated += 1
                    elif failed:
                        tx.statut = TransactionStatut.ECHEC
                        updated += 1

                except (MTNMoMoError, OrangeMoneyError, MoovMoneyError) as e:
                    logger.error("payment_check_failed", tx_id=str(tx.id), operateur=tx.operateur, error=str(e))

            await db.commit()
            logger.info("payment_check_done", checked=len(pending), updated=updated)
        await engine.dispose()

    _run_async(_check())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_chauffeur_payout(self, chauffeur_id: str, amount: int, telephone: str):
    """Reverse les fonds vers le MoMo du chauffeur après livraison."""
    async def _payout():
        from app.integrations.mtn_momo import mtn_momo, MTNMoMoError
        try:
            reference_id = await mtn_momo.transfer(amount, telephone, chauffeur_id)
            logger.info("chauffeur_payout_initiated", chauffeur_id=chauffeur_id, reference_id=reference_id)
            return reference_id
        except MTNMoMoError as exc:
            raise exc

    try:
        return _run_async(_payout())
    except Exception as exc:
        logger.error("chauffeur_payout_failed", chauffeur_id=chauffeur_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def initiate_payment(self, transaction_id: str, amount: int, phone: str, operateur: str):
    """Initie un paiement MoMo (tous opérateurs) et stocke la référence externe."""
    async def _initiate():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.config import get_settings
        from app.models.transaction import Transaction, TransactionOperateur
        from app.integrations.mtn_momo import mtn_momo
        from app.integrations.orange_money import orange_money
        from app.integrations.moov_money import moov_money
        from uuid import UUID

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with SessionLocal() as db:
            tx = await db.get(Transaction, UUID(transaction_id))
            if not tx:
                return

            if operateur == TransactionOperateur.MTN_MOMO:
                ref = await mtn_momo.request_to_pay(amount, phone, transaction_id)
                tx.reference_externe = ref
            elif operateur == TransactionOperateur.ORANGE_MONEY:
                result = await orange_money.initiate_payment(amount, phone, transaction_id)
                tx.reference_externe = result.get("order_id") or transaction_id
            elif operateur == TransactionOperateur.MOOV_MONEY:
                ref = await moov_money.collect(amount, phone, transaction_id)
                tx.reference_externe = ref

            await db.commit()
        await engine.dispose()

    try:
        _run_async(_initiate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


# Alias pour compatibilité avec l'ancienne tâche
check_pending_momo = check_pending_payments
initiate_momo_payment = initiate_payment