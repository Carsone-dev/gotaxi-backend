from app.config import get_settings
from app.core.logging import logger

settings = get_settings()

_app_initialized = False


def _init_firebase():
    global _app_initialized
    if _app_initialized:
        return
    import firebase_admin
    from firebase_admin import credentials
    import os
    if not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
        logger.warning("firebase_credentials_missing", path=settings.FIREBASE_CREDENTIALS_PATH)
        return
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    _app_initialized = True


def send_push(token: str, title: str, body: str, data: dict | None = None) -> str | None:
    _init_firebase()
    if not _app_initialized:
        logger.warning("firebase_not_initialized", token=token[:20])
        return None
    from firebase_admin import messaging
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default")
                )
            ),
        )
        response = messaging.send(message)
        logger.info("push_sent", token=token[:20], response=response)
        return response
    except Exception as e:
        logger.error("push_failed", token=token[:20], error=str(e))
        raise


def send_push_multicast(tokens: list[str], title: str, body: str, data: dict | None = None) -> None:
    _init_firebase()
    if not _app_initialized or not tokens:
        return
    from firebase_admin import messaging
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens,
    )
    response = messaging.send_each_for_multicast(message)
    logger.info("push_multicast", total=len(tokens), success=response.success_count, failure=response.failure_count)