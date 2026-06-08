from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client


def send_sms(to: str, body: str) -> str | None:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("twilio_not_configured", to=to, body=body[:50])
        return None
    try:
        message = _get_client().messages.create(
            from_=settings.TWILIO_FROM_NUMBER,
            to=to,
            body=body,
        )
        logger.info("sms_sent", to=to, sid=message.sid)
        return message.sid
    except TwilioRestException as e:
        logger.error("sms_failed", to=to, error=str(e))
        raise


def send_otp_sms(telephone: str, code: str) -> str | None:
    return send_sms(telephone, f"GoTaxi : votre code de vérification est {code}. Valide 5 min.")


def send_delivery_notification(telephone: str, reference: str, code_retrait: str) -> str | None:
    return send_sms(
        telephone,
        f"GoTaxi : un colis vous est destiné (réf {reference}). Code retrait : {code_retrait}.",
    )


def send_delivery_confirmation(telephone: str, reference: str) -> str | None:
    return send_sms(
        telephone,
        f"GoTaxi : votre colis {reference} a été livré avec succès.",
    )