from app.tasks.celery_app import celery_app
from app.core.logging import logger


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_push_notification(self, token: str, title: str, body: str, data: dict | None = None):
    from app.integrations.fcm import send_push
    try:
        send_push(token, title, body, data)
    except Exception as exc:
        logger.error("push_task_failed", token=token[:20], error=str(exc))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def send_push_multicast_task(self, tokens: list[str], title: str, body: str, data: dict | None = None):
    from app.integrations.fcm import send_push_multicast
    try:
        send_push_multicast(tokens, title, body, data)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


@celery_app.task
def notify_new_reservation(chauffeur_fcm_token: str, client_nom: str, nombre_places: int, reservation_id: str):
    send_push_notification.delay(
        chauffeur_fcm_token,
        "Nouvelle réservation",
        f"{client_nom} veut réserver {nombre_places} place(s)",
        {"type": "reservation", "reservation_id": reservation_id},
    )


@celery_app.task
def notify_reservation_accepted(client_fcm_token: str, ville_depart: str, ville_arrivee: str, reservation_id: str):
    send_push_notification.delay(
        client_fcm_token,
        "Réservation confirmée",
        f"Votre réservation {ville_depart} → {ville_arrivee} est confirmée",
        {"type": "reservation", "reservation_id": reservation_id},
    )


@celery_app.task
def notify_colis_status(user_fcm_token: str, code_suivi: str, statut: str, colis_id: str):
    messages = {
        "CONFIRME": "Votre colis a été accepté par le chauffeur",
        "EN_TRANSIT": "Votre colis est en route",
        "LIVRE": "Votre colis a été livré avec succès",
        "ANNULE": "Votre colis a été annulé",
    }
    body = messages.get(statut, f"Statut mis à jour : {statut}")
    send_push_notification.delay(
        user_fcm_token,
        f"Colis {code_suivi}",
        body,
        {"type": "colis", "colis_id": colis_id, "statut": statut},
    )