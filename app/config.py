from functools import lru_cache
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "gotaxi-backend"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: list[str] = []
    CORS_ORIGINS: list[str] = []

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 300

    # Celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # JWT
    JWT_PRIVATE_KEY_PATH: str = "./keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "./keys/public.pem"
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # OTP
    OTP_EXPIRE_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5

    # Mobile Money — MTN MoMo (Collections)
    MTN_MOMO_API_URL: str = ""
    MTN_MOMO_SUBSCRIPTION_KEY: str = ""
    MTN_MOMO_API_USER: str = ""
    MTN_MOMO_API_KEY: str = ""
    MTN_MOMO_TARGET_ENV: str = "sandbox"
    # MTN MoMo — Disbursements (optionnel, fallback sur collection si vide)
    MTN_MOMO_DISBURSE_SUB_KEY: str = ""
    MTN_MOMO_DISBURSE_API_USER: str = ""
    MTN_MOMO_DISBURSE_API_KEY: str = ""

    MOOV_MONEY_API_URL: str = ""
    MOOV_MONEY_MERCHANT_ID: str = ""
    MOOV_MONEY_SECRET: str = ""

    ORANGE_MONEY_API_URL: str = ""
    ORANGE_MONEY_CLIENT_ID: str = ""
    ORANGE_MONEY_CLIENT_SECRET: str = ""

    # Celtis (Celtiis Bénin — BiBi Money)
    CELTIS_API_URL: str = "https://api-sandbox.celtiis.bj"
    CELTIS_CLIENT_ID: str = ""
    CELTIS_CLIENT_SECRET: str = ""
    CELTIS_MERCHANT_ID: str = ""

    # FedaPay (agrégateur — sandbox par défaut)
    FEDAPAY_API_URL: str = "https://sandbox-api.fedapay.com/v1"
    FEDAPAY_API_KEY: str = ""

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "./keys/firebase.json"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-west-1"
    AWS_S3_BUCKET: str = "gotaxi-uploads"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()