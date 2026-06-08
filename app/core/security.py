from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _load_key(path: str) -> str:
    with open(path) as f:
        return f.read()


def create_access_token(user_id: UUID, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "jti": str(uuid4()),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload,
        _load_key(settings.JWT_PRIVATE_KEY_PATH),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(user_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid4()),
        "exp": expire,
    }
    return jwt.encode(
        payload,
        _load_key(settings.JWT_PRIVATE_KEY_PATH),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _load_key(settings.JWT_PUBLIC_KEY_PATH),
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        raise ValueError(f"Token invalide: {e}")