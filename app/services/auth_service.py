from datetime import datetime, timezone
from uuid import UUID
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.exceptions import (
    InvalidCredentialsException,
    AccountSuspendedException,
    PhoneAlreadyExistsException,
    UserNotFoundException,
    TokenInvalidException,
    InvalidOTPException,
    OTPMaxAttemptsException,
)
from app.models.user import User, UserStatus
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    OTPVerifyRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    RegisterChauffeurRequest,
    RegisterRequest,
    TokenResponse,
)
from app.utils.otp import generate_and_store_otp, verify_otp

settings = get_settings()
_ACCESS_EXPIRES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


class AuthService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis) -> None:
        self._repo = UserRepository(db)
        self._redis = redis

    async def register(self, payload: RegisterRequest) -> None:
        if await self._repo.telephone_exists(payload.telephone):
            raise PhoneAlreadyExistsException()
        await self._repo.create(
            telephone=payload.telephone,
            nom=payload.nom,
            prenom=payload.prenom,
            password=payload.password,
            email=payload.email,
        )

    async def register_chauffeur(self, payload: RegisterChauffeurRequest) -> TokenResponse:
        if await self._repo.telephone_exists(payload.telephone):
            raise PhoneAlreadyExistsException()
        user = await self._repo.create_chauffeur_user(
            telephone=payload.telephone,
            nom=payload.nom,
            prenom=payload.prenom,
            password=payload.password,
            email=payload.email,
        )
        await self._repo._db.commit()
        return TokenResponse(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id),
            expires_in=_ACCESS_EXPIRES,
        )

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self._repo.get_by_telephone(payload.telephone)
        if not user or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsException()
        if user.statut == UserStatus.SUSPENDU:
            raise AccountSuspendedException()
        if user.statut == UserStatus.SUPPRIME:
            raise InvalidCredentialsException()
        return TokenResponse(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id),
            expires_in=_ACCESS_EXPIRES,
        )

    async def send_otp(self, telephone: str) -> str:
        return await generate_and_store_otp(telephone)

    async def verify_otp_and_activate(self, telephone: str, code: str) -> None:
        await self._verify_otp_safe(telephone, code)
        user = await self._repo.get_by_telephone(telephone)
        if user:
            user.telephone_verifie = True

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        try:
            data = decode_token(refresh_token)
            if data.get("type") != "refresh":
                raise ValueError()
            user_id = UUID(data["sub"])
        except Exception:
            raise TokenInvalidException()
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise TokenInvalidException()
        return TokenResponse(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id),
            expires_in=_ACCESS_EXPIRES,
        )

    async def logout(self, token: str) -> None:
        try:
            data = decode_token(token)
            jti = data["jti"]
            exp = data["exp"]
            ttl = int(exp - datetime.now(timezone.utc).timestamp())
            if ttl > 0:
                await self._redis.set(f"blacklist:{jti}", "1", ex=ttl)
        except Exception:
            pass

    async def forgot_password(self, telephone: str) -> None:
        user = await self._repo.get_by_telephone(telephone)
        if user:
            await generate_and_store_otp(telephone)
            # TODO: send_otp_sms.delay(telephone, code)

    async def reset_password(self, payload: PasswordResetRequest) -> None:
        await self._verify_otp_safe(payload.telephone, payload.code)
        user = await self._repo.get_by_telephone(payload.telephone)
        if not user:
            raise UserNotFoundException()
        user.password_hash = hash_password(payload.new_password)

    async def change_password(self, user: User, payload: PasswordChangeRequest) -> None:
        if not verify_password(payload.current_password, user.password_hash):
            raise InvalidCredentialsException()
        user.password_hash = hash_password(payload.new_password)

    async def _verify_otp_safe(self, telephone: str, code: str) -> None:
        try:
            await verify_otp(telephone, code)
        except ValueError as e:
            msg = str(e)
            if "bloqué" in msg or "Trop de" in msg:
                raise OTPMaxAttemptsException()
            raise InvalidOTPException()