from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    OTPSendRequest,
    OTPVerifyRequest,
    PasswordChangeRequest,
    PasswordForgotRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterChauffeurRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentification"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> AuthService:
    return AuthService(db, redis)


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.register(payload)
    return MessageResponse(message="Inscription réussie. Vérifiez votre téléphone.")


@router.post("/register/chauffeur", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_chauffeur(
    payload: RegisterChauffeurRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.register_chauffeur(payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.login(payload)


@router.post("/otp/send", response_model=MessageResponse)
async def otp_send(
    payload: OTPSendRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.send_otp(payload.telephone)
    return MessageResponse(message="Code OTP envoyé")


@router.post("/otp/verify", response_model=MessageResponse)
async def otp_verify(
    payload: OTPVerifyRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.verify_otp_and_activate(payload.telephone, payload.code)
    return MessageResponse(message="Téléphone vérifié")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.refresh_tokens(payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user: Annotated[User, Depends(get_current_user)],
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.logout(token)
    return MessageResponse(message="Déconnexion réussie")


@router.post("/password/forgot", response_model=MessageResponse)
async def password_forgot(
    payload: PasswordForgotRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.forgot_password(payload.telephone)
    return MessageResponse(message="Si ce numéro est enregistré, un code vous a été envoyé")


@router.post("/password/reset", response_model=MessageResponse)
async def password_reset(
    payload: PasswordResetRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.reset_password(payload)
    return MessageResponse(message="Mot de passe réinitialisé")


@router.post("/password/change", response_model=MessageResponse)
async def password_change(
    payload: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.change_password(current_user, payload)
    return MessageResponse(message="Mot de passe modifié")