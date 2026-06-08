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
def send_daily_admin_report():
    """Génère les KPIs du jour et les envoie aux admins via SMS/email."""
    async def _report():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from sqlalchemy import select, func
        from datetime import date, datetime, timezone, timedelta
        from app.config import get_settings
        from app.models.user import User
        from app.models.voyage import Voyage
        from app.models.colis import Colis
        from app.models.transaction import Transaction, TransactionStatut
        from app.models.reservation import Reservation

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        async with SessionLocal() as db:
            new_users = (await db.execute(
                select(func.count()).select_from(User).where(User.created_at >= yesterday_start)
            )).scalar() or 0

            new_voyages = (await db.execute(
                select(func.count()).select_from(Voyage).where(Voyage.created_at >= yesterday_start)
            )).scalar() or 0

            new_reservations = (await db.execute(
                select(func.count()).select_from(Reservation).where(Reservation.created_at >= yesterday_start)
            )).scalar() or 0

            new_colis = (await db.execute(
                select(func.count()).select_from(Colis).where(Colis.created_at >= yesterday_start)
            )).scalar() or 0

            revenue = (await db.execute(
                select(func.sum(Transaction.montant)).where(
                    Transaction.statut == TransactionStatut.REUSSI,
                    Transaction.created_at >= yesterday_start,
                )
            )).scalar() or 0

        await engine.dispose()

        report = {
            "date": date.today().isoformat(),
            "nouveaux_utilisateurs": new_users,
            "nouveaux_voyages": new_voyages,
            "nouvelles_reservations": new_reservations,
            "nouveaux_colis": new_colis,
            "revenus_xof": revenue,
        }
        logger.info("daily_report", **report)
        # TODO: envoyer par email aux SUPER_ADMIN
        return report

    return _run_async(_report())


@celery_app.task
def generate_weekly_kpi_export():
    """Exporte les KPIs hebdomadaires en CSV et les envoie aux admins."""
    logger.info("weekly_kpi_export_started")
    # TODO: générer CSV et uploader sur S3, puis notifier