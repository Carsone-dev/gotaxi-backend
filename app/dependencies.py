from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, Query, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.core.security import decode_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Type de token invalide")
        user_id = UUID(payload["sub"])
        jti: str | None = payload.get("jti")
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if jti and await redis.exists(f"blacklist:{jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token révoqué",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(User, user_id)
    if not user or user.statut == "SUPPRIME":
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    if user.statut == "SUSPENDU":
        raise HTTPException(status_code=403, detail="Compte suspendu")
    return user


def require_role(*roles: UserRole):
    async def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Permission refusée")
        return user
    return _checker


async def get_current_user_ws(websocket: WebSocket, db: AsyncSession = Depends(get_db)) -> User:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        raise HTTPException(status_code=401, detail="Token manquant")
    try:
        payload = decode_token(token)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        await websocket.close(code=1008)
        raise HTTPException(status_code=401, detail="Token invalide")

    user = await db.get(User, user_id)
    if not user:
        await websocket.close(code=1008)
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user


def pagination_params(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict:
    return {"offset": (page - 1) * size, "limit": size, "page": page, "size": size}