from datetime import timezone, datetime
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.websockets.manager import manager
from app.core.database import async_session_factory
from app.core.security import decode_token
from app.models.chauffeur import Chauffeur
from app.models.voyage import Voyage, VoyageStatut

router = APIRouter()


def _chauffeur_status(chauffeur: Chauffeur, active_voyage_id: UUID | None) -> str:
    if active_voyage_id:
        return "in_trip"
    return "available"


async def _build_fleet_snapshot(db: AsyncSession) -> dict:
    result = await db.execute(
        select(Chauffeur)
        .options(selectinload(Chauffeur.user))
        .where(
            Chauffeur.en_ligne == True,
            Chauffeur.derniere_position_lat != None,
            Chauffeur.derniere_position_lng != None,
        )
    )
    chauffeurs = result.scalars().all()

    voyages_result = await db.execute(
        select(Voyage).where(Voyage.statut == VoyageStatut.EN_COURS)
    )
    active_voyages = {v.chauffeur_id: v for v in voyages_result.scalars().all()}

    drivers = []
    trips = []
    for c in chauffeurs:
        voyage = active_voyages.get(c.id)
        drivers.append({
            "id": str(c.id),
            "user_id": str(c.user_id),
            "nom": c.user.nom,
            "prenom": c.user.prenom,
            "photo_url": c.user.photo_url,
            "lat": float(c.derniere_position_lat),
            "lng": float(c.derniere_position_lng),
            "vitesse": 0,
            "heading": 0,
            "status": _chauffeur_status(c, voyage.id if voyage else None),
            "voyage_id": str(voyage.id) if voyage else None,
        })
        if voyage:
            trips.append({
                "id": str(voyage.id),
                "chauffeur_id": str(c.id),
                "ville_depart": voyage.ville_depart,
                "ville_arrivee": voyage.ville_arrivee,
                "date_depart": voyage.date_depart.isoformat(),
                "passagers": 0,
                "statut": voyage.statut,
            })

    return {"type": "fleet_snapshot", "drivers": drivers, "trips": trips}


_ADMIN_ROLES = {"ADMIN", "SUPER_ADMIN"}


@router.websocket("/ws/admin/activity")
async def ws_admin_activity(ws: WebSocket, token: str = ""):
    try:
        payload = decode_token(token)
        if payload.get("role") not in _ADMIN_ROLES:
            await ws.close(code=1008)
            return
    except Exception:
        await ws.close(code=1008)
        return

    channel = "admin:activity"
    await manager.connect(channel, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        manager.disconnect(channel, ws)


@router.websocket("/ws/admin/fleet")
async def ws_admin_fleet(ws: WebSocket):
    channel = "admin:fleet"
    await manager.connect(channel, ws)
    try:
        async with async_session_factory() as db:
            snapshot = await _build_fleet_snapshot(db)
        await ws.send_json(snapshot)

        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        manager.disconnect(channel, ws)


@router.websocket("/ws/tracking/voyage/{voyage_id}")
async def tracking_voyage(ws: WebSocket, voyage_id: UUID):
    channel = f"tracking:voyage:{voyage_id}"
    await manager.connect(channel, ws)
    try:
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        manager.disconnect(channel, ws)


@router.websocket("/ws/tracking/colis/{colis_id}")
async def tracking_colis(ws: WebSocket, colis_id: UUID):
    channel = f"tracking:colis:{colis_id}"
    await manager.connect(channel, ws)
    try:
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        manager.disconnect(channel, ws)


@router.websocket("/ws/notifications")
async def ws_notifications(ws: WebSocket):
    channel = "notifications:global"
    await manager.connect(channel, ws)
    try:
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        manager.disconnect(channel, ws)
