from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "gotaxi",
    broker=settings.CELERY_BROKER_URL or "redis://localhost:6379/1",
    backend=settings.CELERY_RESULT_BACKEND or "redis://localhost:6379/2",
    include=[
        "app.tasks.sms_tasks",
        "app.tasks.push_tasks",
        "app.tasks.payment_tasks",
        "app.tasks.reports_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Porto-Novo",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "check-pending-payments": {
            "task": "app.tasks.payment_tasks.check_pending_payments",
            "schedule": 60.0,
        },
        "send-daily-admin-report": {
            "task": "app.tasks.reports_tasks.send_daily_admin_report",
            "schedule": 28800.0,  # 8h
        },
        "cleanup-expired-otps": {
            "task": "app.tasks.sms_tasks.cleanup_expired_sessions",
            "schedule": 3600.0,
        },
    },
)