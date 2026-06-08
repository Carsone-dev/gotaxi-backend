from app.tasks.celery_app import celery_app
from app.core.logging import logger


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def send_otp_sms(self, telephone: str, code: str):
    from app.integrations.twilio_sms import send_otp_sms as _send
    try:
        _send(telephone, code)
        logger.info("sms_task_otp_sent", telephone=telephone)
    except Exception as exc:
        logger.error("sms_task_otp_failed", telephone=telephone, error=str(exc))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def send_delivery_sms(self, telephone: str, reference: str, code_retrait: str):
    from app.integrations.twilio_sms import send_delivery_notification as _send
    try:
        _send(telephone, reference, code_retrait)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def send_delivery_confirmation_sms(self, telephone: str, reference: str):
    from app.integrations.twilio_sms import send_delivery_confirmation as _send
    try:
        _send(telephone, reference)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task
def cleanup_expired_sessions():
    """Placeholder — Redis TTL gère déjà l'expiration des OTP."""
    logger.info("cleanup_expired_sessions_noop")