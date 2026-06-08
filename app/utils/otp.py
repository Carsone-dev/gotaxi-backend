import random
import string
from app.core import redis_client as _redis_mod
from app.config import get_settings

settings = get_settings()


def _otp_key(telephone: str) -> str:
    return f"otp:{telephone}"


def _lock_key(telephone: str) -> str:
    return f"otp_lock:{telephone}"


async def generate_and_store_otp(telephone: str) -> str:
    code = "".join(random.choices(string.digits, k=6))
    await _redis_mod.redis_client.set(
        _otp_key(telephone),
        f"{code}:0",
        ex=settings.OTP_EXPIRE_SECONDS,
    )
    return code


async def verify_otp(telephone: str, code: str) -> bool:
    if await _redis_mod.redis_client.exists(_lock_key(telephone)):
        raise ValueError("Compte bloqué temporairement. Réessayez dans 30 min.")

    stored = await _redis_mod.redis_client.get(_otp_key(telephone))
    if not stored:
        raise ValueError("Code OTP expiré ou invalide")

    stored_code, attempts_str = stored.split(":")
    attempts = int(attempts_str) + 1

    if attempts >= settings.OTP_MAX_ATTEMPTS:
        await _redis_mod.redis_client.delete(_otp_key(telephone))
        await _redis_mod.redis_client.set(_lock_key(telephone), "1", ex=1800)
        raise ValueError("Trop de tentatives. Compte bloqué 30 min.")

    if code != stored_code:
        await _redis_mod.redis_client.set(
            _otp_key(telephone),
            f"{stored_code}:{attempts}",
            ex=settings.OTP_EXPIRE_SECONDS,
        )
        raise ValueError("Code OTP invalide")

    await _redis_mod.redis_client.delete(_otp_key(telephone))
    return True