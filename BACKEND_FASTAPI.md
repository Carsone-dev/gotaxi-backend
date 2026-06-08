# 🚀 GoTaxi — Guide complet du Backend FastAPI

> **Version :** 1.0.0
> **Référence :** GT-BACKEND-2026-001
> **Stack :** Python 3.12 · FastAPI · PostgreSQL 16 · Redis 7 · Celery · JWT
> **Cible :** Développeur backend senior

Ce document est le **manuel d'exécution complet** pour bâtir l'API GoTaxi de zéro jusqu'à la production. Il couvre l'architecture, la structure du projet, tous les modèles, schémas, **tous les endpoints (60+)**, la sécurité, les workflows, les tests et le déploiement.

---

## 📑 Sommaire

1. [Vue d'ensemble & principes](#1-vue-densemble--principes)
2. [Stack technique](#2-stack-technique)
3. [Structure du projet](#3-structure-du-projet)
4. [Configuration de l'environnement](#4-configuration-de-lenvironnement)
5. [Modèles SQLAlchemy](#5-modèles-sqlalchemy)
6. [Schémas Pydantic](#6-schémas-pydantic)
7. [Authentification & sécurité](#7-authentification--sécurité)
8. [Endpoints API (référence complète)](#8-endpoints-api-référence-complète)
9. [WebSockets & temps réel](#9-websockets--temps-réel)
10. [Intégrations externes](#10-intégrations-externes)
11. [Tâches asynchrones (Celery)](#11-tâches-asynchrones-celery)
12. [Tests](#12-tests)
13. [Déploiement & DevOps](#13-déploiement--devops)
14. [Conventions de code](#14-conventions-de-code)

---

## 1. Vue d'ensemble & principes

### 1.1 Mission du backend

Le backend GoTaxi orchestre :
- **Authentification** des clients, chauffeurs, administrateurs (JWT + OTP SMS)
- **Gestion des voyages** interurbains (création, recherche, réservation)
- **Livraison de colis** (workflow validation → assignation → livraison)
- **Suivi GPS temps réel** des chauffeurs (WebSockets)
- **Wallet** intégré + intégrations Mobile Money (MTN MoMo, Moov, Orange)
- **Notifications** push (FCM) + SMS
- **Dashboard admin** (KPIs, modération, audit)

### 1.2 Principes architecturaux

- **Architecture en couches** : `routers → services → repositories → models`
- **Responsibility-driven** : chaque fichier fait UNE chose
- **Async first** : tous les endpoints I/O sont `async` (asyncpg, httpx)
- **Schema-first** : Pydantic valide TOUTES les entrées et sorties
- **Domain-driven** : modules organisés par domaine métier (voyages, colis, wallet)
- **Stateless** : aucun état stocké côté serveur, scalable horizontalement
- **Observable** : logs structurés (JSON), traces OpenTelemetry, métriques Prometheus

### 1.3 Acteurs et rôles

| Rôle | Description | Permissions principales |
|------|-------------|------------------------|
| `CLIENT` | Voyageur ou expéditeur | Réserver trajets, envoyer colis, recharger wallet |
| `CHAUFFEUR` | Transporteur partenaire | Publier trajets, accepter réservations/colis, mettre à jour position GPS |
| `ADMIN` | Modérateur opérationnel | Valider colis, modérer avis, gérer utilisateurs |
| `SUPER_ADMIN` | Direction GoTaxi | Tout + paramètres système, finance, audit |

---

## 2. Stack technique

### 2.1 Dépendances principales

```toml
# pyproject.toml
[project]
name = "gotaxi-backend"
version = "1.0.0"
requires-python = ">=3.12"

dependencies = [
    "fastapi==0.115.*",
    "uvicorn[standard]==0.32.*",
    "pydantic==2.9.*",
    "pydantic-settings==2.6.*",
    "sqlalchemy[asyncio]==2.0.*",
    "asyncpg==0.30.*",
    "alembic==1.14.*",
    "redis[hiredis]==5.2.*",
    "celery[redis]==5.4.*",
    "python-jose[cryptography]==3.3.*",
    "passlib[bcrypt]==1.7.*",
    "python-multipart==0.0.*",
    "httpx==0.28.*",
    "firebase-admin==6.6.*",
    "twilio==9.3.*",
    "boto3==1.35.*",
    "pillow==11.0.*",
    "python-dotenv==1.0.*",
    "structlog==24.4.*",
    "prometheus-fastapi-instrumentator==7.0.*",
    "geoalchemy2==0.16.*",
    "shapely==2.0.*",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.*",
    "pytest-asyncio==0.24.*",
    "pytest-cov==6.0.*",
    "httpx==0.28.*",
    "faker==33.1.*",
    "ruff==0.8.*",
    "mypy==1.13.*",
    "pre-commit==4.0.*",
]
```

### 2.2 Pourquoi ces choix ?

| Choix | Justification |
|-------|---------------|
| **FastAPI** | Performance (Starlette + Pydantic), génération auto OpenAPI, support async natif |
| **PostgreSQL 16 + PostGIS** | ACID, requêtes géo-spatiales pour le tracking GPS |
| **Redis** | Cache rapide, pub/sub pour WebSockets, broker Celery, sessions OTP |
| **Celery** | Tâches longues (envoi SMS, callbacks MoMo, génération PDF) |
| **Alembic** | Migrations versionnées, rollback safe |
| **JWT (RS256)** | Stateless, signature asymétrique (rotation des clés sans invalider) |

---

## 3. Structure du projet

```
gotaxi-backend/
├── alembic/                          # Migrations DB
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_voyages.py
│   │   └── ...
│   └── env.py
├── app/
│   ├── __init__.py
│   ├── main.py                       # Point d'entrée FastAPI
│   ├── config.py                     # Settings Pydantic
│   ├── dependencies.py               # Dépendances communes (DB, auth)
│   ├── exceptions.py                 # Exceptions personnalisées
│   ├── middlewares/
│   │   ├── auth.py
│   │   ├── cors.py
│   │   ├── logging.py
│   │   └── rate_limit.py
│   ├── core/
│   │   ├── security.py               # JWT, hashing, OTP
│   │   ├── database.py               # Sessions SQLAlchemy
│   │   ├── redis_client.py
│   │   └── logging.py
│   ├── models/                       # SQLAlchemy ORM
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── chauffeur.py
│   │   ├── vehicule.py
│   │   ├── voyage.py
│   │   ├── reservation.py
│   │   ├── colis.py
│   │   ├── suivi.py
│   │   ├── wallet.py
│   │   ├── transaction.py
│   │   ├── avis.py
│   │   ├── notification.py
│   │   └── audit.py
│   ├── schemas/                      # Pydantic
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── voyage.py
│   │   ├── reservation.py
│   │   ├── colis.py
│   │   ├── wallet.py
│   │   └── common.py
│   ├── repositories/                 # Couche data access
│   │   ├── base.py
│   │   ├── user_repo.py
│   │   ├── voyage_repo.py
│   │   ├── colis_repo.py
│   │   └── wallet_repo.py
│   ├── services/                     # Logique métier
│   │   ├── auth_service.py
│   │   ├── voyage_service.py
│   │   ├── colis_service.py
│   │   ├── geoloc_service.py
│   │   ├── wallet_service.py
│   │   ├── notif_service.py
│   │   ├── pricing_service.py
│   │   └── matching_service.py
│   ├── routers/                      # Endpoints HTTP
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── chauffeurs.py
│   │   ├── voyages.py
│   │   ├── reservations.py
│   │   ├── colis.py
│   │   ├── suivi.py
│   │   ├── wallet.py
│   │   ├── transactions.py
│   │   ├── avis.py
│   │   ├── notifications.py
│   │   ├── admin.py
│   │   └── public.py
│   ├── websockets/
│   │   ├── manager.py
│   │   ├── tracking.py
│   │   └── notifications.py
│   ├── tasks/                        # Celery
│   │   ├── celery_app.py
│   │   ├── sms_tasks.py
│   │   ├── push_tasks.py
│   │   ├── payment_tasks.py
│   │   └── reports_tasks.py
│   ├── integrations/
│   │   ├── mtn_momo.py
│   │   ├── moov_money.py
│   │   ├── orange_money.py
│   │   ├── fcm.py
│   │   ├── twilio_sms.py
│   │   └── s3_storage.py
│   └── utils/
│       ├── otp.py
│       ├── pagination.py
│       ├── validators.py
│       └── geo.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/
│   ├── seed_db.py
│   ├── create_admin.py
│   └── export_kpis.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── pyproject.toml
├── alembic.ini
├── ruff.toml
└── README.md
```

---

## 4. Configuration de l'environnement

### 4.1 Variables d'environnement (`.env.example`)

```bash
# Application
APP_NAME=gotaxi-backend
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=http://localhost:3000,https://app.gotaxi.bj

# Base de données
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=gotaxi
POSTGRES_PASSWORD=changeme
POSTGRES_DB=gotaxi
DATABASE_URL=postgresql+asyncpg://gotaxi:changeme@localhost:5432/gotaxi
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=300

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# JWT
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem
JWT_ALGORITHM=RS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# OTP
OTP_EXPIRE_SECONDS=300
OTP_MAX_ATTEMPTS=5

# Mobile Money
MTN_MOMO_API_URL=https://sandbox.momodeveloper.mtn.com
MTN_MOMO_SUBSCRIPTION_KEY=
MTN_MOMO_API_USER=
MTN_MOMO_API_KEY=
MTN_MOMO_TARGET_ENV=sandbox

MOOV_MONEY_API_URL=
MOOV_MONEY_MERCHANT_ID=
MOOV_MONEY_SECRET=

ORANGE_MONEY_API_URL=
ORANGE_MONEY_CLIENT_ID=
ORANGE_MONEY_CLIENT_SECRET=

# Twilio (SMS)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=+229xxx

# Firebase (Push)
FIREBASE_CREDENTIALS_PATH=./keys/firebase.json

# AWS S3 (uploads)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=eu-west-1
AWS_S3_BUCKET=gotaxi-uploads
```

### 4.2 Settings Pydantic (`app/config.py`)

```python
from functools import lru_cache
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application
    APP_NAME: str
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: list[str] = []
    CORS_ORIGINS: list[str] = []

    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: RedisDsn
    REDIS_CACHE_TTL: int = 300

    # JWT
    JWT_PRIVATE_KEY_PATH: str
    JWT_PUBLIC_KEY_PATH: str
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # OTP
    OTP_EXPIRE_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5

    # Mobile Money & autres clés
    MTN_MOMO_API_URL: str = ""
    MTN_MOMO_SUBSCRIPTION_KEY: str = ""
    # ... autres champs

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## 5. Modèles SQLAlchemy

### 5.1 Base et conventions

```python
# app/models/base.py
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
```

### 5.2 Modèle utilisateur

```python
# app/models/user.py
import enum
from sqlalchemy import String, Boolean, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class UserRole(str, enum.Enum):
    CLIENT = "CLIENT"
    CHAUFFEUR = "CHAUFFEUR"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class UserStatus(str, enum.Enum):
    ACTIF = "ACTIF"
    SUSPENDU = "SUSPENDU"
    EN_ATTENTE_KYC = "EN_ATTENTE_KYC"
    SUPPRIME = "SUPPRIME"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    telephone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CLIENT)
    statut: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIF)
    telephone_verifie: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verifie: Mapped[bool] = mapped_column(Boolean, default=False)
    note_moyenne: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    nombre_avis: Mapped[int] = mapped_column(default=0)
    fcm_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    langue: Mapped[str] = mapped_column(String(5), default="fr")

    chauffeur = relationship("Chauffeur", back_populates="user", uselist=False)
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    reservations = relationship("Reservation", back_populates="client")
```

### 5.3 Modèle Chauffeur

```python
# app/models/chauffeur.py
from datetime import date
from uuid import UUID
from sqlalchemy import String, Boolean, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Chauffeur(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chauffeurs"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    cin_numero: Mapped[str] = mapped_column(String(50))
    cin_url: Mapped[str] = mapped_column(String(500))
    permis_numero: Mapped[str] = mapped_column(String(50))
    permis_url: Mapped[str] = mapped_column(String(500))
    permis_expiration: Mapped[date] = mapped_column(Date)
    casier_judiciaire_url: Mapped[str | None] = mapped_column(String(500))
    kyc_valide: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_valide_le: Mapped[date | None] = mapped_column(Date, nullable=True)
    autorisation_transfrontaliere: Mapped[bool] = mapped_column(Boolean, default=False)
    en_ligne: Mapped[bool] = mapped_column(Boolean, default=False)
    derniere_position_lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    derniere_position_lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    derniere_activite: Mapped[date | None] = mapped_column(Date, nullable=True)
    nombre_trajets: Mapped[int] = mapped_column(default=0)
    revenus_total: Mapped[int] = mapped_column(default=0)

    user = relationship("User", back_populates="chauffeur")
    vehicules = relationship("Vehicule", back_populates="chauffeur")
    voyages = relationship("Voyage", back_populates="chauffeur")
```

### 5.4 Modèle Voyage

```python
# app/models/voyage.py
import enum
from datetime import datetime
from uuid import UUID
from sqlalchemy import String, Integer, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class VoyageStatut(str, enum.Enum):
    PUBLIE = "PUBLIE"
    COMPLET = "COMPLET"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    ANNULE = "ANNULE"


class Voyage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "voyages"

    chauffeur_id: Mapped[UUID] = mapped_column(ForeignKey("chauffeurs.id"))
    vehicule_id: Mapped[UUID] = mapped_column(ForeignKey("vehicules.id"))
    ville_depart: Mapped[str] = mapped_column(String(100))
    ville_arrivee: Mapped[str] = mapped_column(String(100))
    point_depart: Mapped[str] = mapped_column(String(255))
    point_arrivee: Mapped[str] = mapped_column(String(255))
    lat_depart: Mapped[float] = mapped_column()
    lng_depart: Mapped[float] = mapped_column()
    lat_arrivee: Mapped[float] = mapped_column()
    lng_arrivee: Mapped[float] = mapped_column()
    date_depart: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    date_arrivee_estimee: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    prix_par_place: Mapped[int] = mapped_column(Integer)
    nombre_places_total: Mapped[int] = mapped_column(Integer)
    nombre_places_restantes: Mapped[int] = mapped_column(Integer)
    accepte_colis: Mapped[bool] = mapped_column(Boolean, default=True)
    climatise: Mapped[bool] = mapped_column(Boolean, default=False)
    non_fumeur: Mapped[bool] = mapped_column(Boolean, default=True)
    statut: Mapped[VoyageStatut] = mapped_column(Enum(VoyageStatut), default=VoyageStatut.PUBLIE)
    distance_km: Mapped[int | None] = mapped_column(nullable=True)

    chauffeur = relationship("Chauffeur", back_populates="voyages")
    vehicule = relationship("Vehicule")
    reservations = relationship("Reservation", back_populates="voyage")
    colis = relationship("Colis", back_populates="voyage")
```

### 5.5 Modèle Réservation

```python
# app/models/reservation.py
import enum
from uuid import UUID
from sqlalchemy import Integer, ForeignKey, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class ReservationStatut(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    CONFIRMEE = "CONFIRMEE"
    REFUSEE = "REFUSEE"
    ANNULEE = "ANNULEE"
    TERMINEE = "TERMINEE"


class Reservation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reservations"

    voyage_id: Mapped[UUID] = mapped_column(ForeignKey("voyages.id"))
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    nombre_places: Mapped[int] = mapped_column(Integer)
    prix_total: Mapped[int] = mapped_column(Integer)
    statut: Mapped[ReservationStatut] = mapped_column(Enum(ReservationStatut), default=ReservationStatut.EN_ATTENTE)
    code_confirmation: Mapped[str] = mapped_column(String(6))
    transaction_id: Mapped[UUID | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)

    voyage = relationship("Voyage", back_populates="reservations")
    client = relationship("User", back_populates="reservations")
```

### 5.6 Modèle Colis

```python
# app/models/colis.py
import enum
from datetime import datetime
from uuid import UUID
from sqlalchemy import String, Integer, Numeric, ForeignKey, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class ColisType(str, enum.Enum):
    DOCUMENT = "DOCUMENT"
    PETIT = "PETIT"
    MOYEN = "MOYEN"
    GRAND = "GRAND"


class ColisStatut(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE = "VALIDE"
    ASSIGNE = "ASSIGNE"
    RECUPERE = "RECUPERE"
    EN_ROUTE = "EN_ROUTE"
    LIVRE = "LIVRE"
    ANNULE = "ANNULE"
    LITIGE = "LITIGE"


class Colis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "colis"

    reference: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    expediteur_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    voyage_id: Mapped[UUID | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    chauffeur_id: Mapped[UUID | None] = mapped_column(ForeignKey("chauffeurs.id"), nullable=True)
    type_colis: Mapped[ColisType] = mapped_column(Enum(ColisType))
    poids_kg: Mapped[float] = mapped_column(Numeric(5, 2))
    description: Mapped[str] = mapped_column(String(500))
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ville_depart: Mapped[str] = mapped_column(String(100))
    ville_arrivee: Mapped[str] = mapped_column(String(100))
    adresse_depart: Mapped[str] = mapped_column(String(500))
    adresse_arrivee: Mapped[str] = mapped_column(String(500))
    destinataire_nom: Mapped[str] = mapped_column(String(100))
    destinataire_telephone: Mapped[str] = mapped_column(String(20))
    code_retrait: Mapped[str] = mapped_column(String(8))
    prix: Mapped[int] = mapped_column(Integer)
    statut: Mapped[ColisStatut] = mapped_column(Enum(ColisStatut), default=ColisStatut.EN_ATTENTE)
    date_retrait_prevu: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_livraison_prevue: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    date_livraison_reelle: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    expediteur = relationship("User", foreign_keys=[expediteur_id])
    voyage = relationship("Voyage", back_populates="colis")
    chauffeur = relationship("Chauffeur")
    suivi = relationship("SuiviColis", back_populates="colis", order_by="SuiviColis.created_at")
```

### 5.7 Autres modèles essentiels

```python
# app/models/wallet.py
class Wallet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wallets"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    solde: Mapped[int] = mapped_column(Integer, default=0)  # FCFA, en entier
    devise: Mapped[str] = mapped_column(String(3), default="XOF")
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


# app/models/transaction.py
class TransactionType(str, enum.Enum):
    RECHARGE = "RECHARGE"
    PAIEMENT_VOYAGE = "PAIEMENT_VOYAGE"
    PAIEMENT_COLIS = "PAIEMENT_COLIS"
    REVERSEMENT = "REVERSEMENT"
    REMBOURSEMENT = "REMBOURSEMENT"
    COMMISSION = "COMMISSION"


class TransactionStatut(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    EN_COURS = "EN_COURS"
    REUSSI = "REUSSI"
    ECHEC = "ECHEC"
    ANNULE = "ANNULE"


class TransactionOperateur(str, enum.Enum):
    MTN_MOMO = "MTN_MOMO"
    MOOV_MONEY = "MOOV_MONEY"
    ORANGE_MONEY = "ORANGE_MONEY"
    WALLET = "WALLET"


# app/models/suivi.py
class SuiviColis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "suivi_colis"
    colis_id: Mapped[UUID] = mapped_column(ForeignKey("colis.id"))
    statut: Mapped[ColisStatut] = mapped_column(Enum(ColisStatut))
    description: Mapped[str] = mapped_column(String(500))
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lng: Mapped[float | None] = mapped_column(nullable=True)
    ville: Mapped[str | None] = mapped_column(String(100), nullable=True)


# app/models/avis.py
class Avis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "avis"
    auteur_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    cible_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    voyage_id: Mapped[UUID | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    note: Mapped[int] = mapped_column(Integer)  # 1 à 5
    commentaire: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tags: Mapped[list[str]] = mapped_column(default=list)
    signale: Mapped[bool] = mapped_column(Boolean, default=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
```

---

## 6. Schémas Pydantic

### 6.1 Conventions

- `*Create` : payload de création (POST)
- `*Update` : payload de modification (PATCH)
- `*Read` : réponse renvoyée au client
- `*InDB` : structure interne (pas exposée)

### 6.2 Exemples clés

```python
# app/schemas/auth.py
from pydantic import BaseModel, Field, field_validator
import re


class TelephoneStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not re.match(r"^\+229\d{8}$|^\+228\d{8}$", v):
            raise ValueError("Format téléphone invalide (ex: +22997123456)")
        return v


class RegisterRequest(BaseModel):
    telephone: str = Field(..., pattern=r"^\+229\d{8}$|^\+228\d{8}$")
    nom: str = Field(..., min_length=2, max_length=100)
    prenom: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
    email: str | None = None


class LoginRequest(BaseModel):
    telephone: str
    password: str


class OTPVerifyRequest(BaseModel):
    telephone: str
    code: str = Field(..., min_length=4, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # secondes


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# app/schemas/voyage.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class VoyageCreate(BaseModel):
    ville_depart: str
    ville_arrivee: str
    point_depart: str
    point_arrivee: str
    lat_depart: float
    lng_depart: float
    lat_arrivee: float
    lng_arrivee: float
    date_depart: datetime
    prix_par_place: int = Field(..., ge=500, le=100000)
    nombre_places_total: int = Field(..., ge=1, le=8)
    accepte_colis: bool = True
    climatise: bool = False
    non_fumeur: bool = True
    vehicule_id: UUID


class VoyageRead(BaseModel):
    id: UUID
    ville_depart: str
    ville_arrivee: str
    date_depart: datetime
    date_arrivee_estimee: datetime
    prix_par_place: int
    nombre_places_restantes: int
    nombre_places_total: int
    accepte_colis: bool
    climatise: bool
    statut: str
    chauffeur: "ChauffeurPublic"
    distance_km: int | None

    model_config = {"from_attributes": True}


class VoyageSearch(BaseModel):
    ville_depart: str
    ville_arrivee: str
    date_depart: datetime
    nombre_places: int = 1
    accepte_colis: bool | None = None
    climatise: bool | None = None
    prix_max: int | None = None
```

---

## 7. Authentification & sécurité

### 7.1 Génération des clés JWT (RS256)

```bash
# Une fois, en setup initial
mkdir -p keys
openssl genrsa -out keys/private.pem 4096
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
chmod 600 keys/private.pem
```

### 7.2 Module sécurité

```python
# app/core/security.py
from datetime import datetime, timedelta, timezone
from uuid import UUID
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
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
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
```

### 7.3 Dépendance d'authentification

```python
# app/dependencies.py
from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Type de token invalide")
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
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
```

### 7.4 OTP (vérification téléphone)

- Génération aléatoire 4-6 chiffres, stocké en Redis avec TTL 5 min
- Clé : `otp:{telephone}`, valeur : `{code}:{tentatives}`
- Limite 5 tentatives, blocage 30 min après dépassement
- Envoi via Twilio (SMS) ou opérateur local

---

## 8. Endpoints API (référence complète)

> **Convention :** tous les endpoints sont préfixés par `/api/v1`. Les statuts succès retournent 200/201/204. Les schémas Pydantic font l'objet de la doc OpenAPI auto-générée.

### 8.1 Authentification — `/auth`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `POST` | `/auth/register` | Inscription d'un client | Public |
| `POST` | `/auth/register/chauffeur` | Inscription chauffeur (multipart : pièces) | Public |
| `POST` | `/auth/login` | Connexion (téléphone + password) | Public |
| `POST` | `/auth/otp/send` | Envoyer code OTP par SMS | Public |
| `POST` | `/auth/otp/verify` | Vérifier le code OTP | Public |
| `POST` | `/auth/refresh` | Renouveler l'access token | Refresh token |
| `POST` | `/auth/logout` | Déconnexion (blacklist token) | Bearer |
| `POST` | `/auth/password/forgot` | Demande reset par OTP | Public |
| `POST` | `/auth/password/reset` | Reset avec OTP + nouveau mdp | Public |
| `POST` | `/auth/password/change` | Modifier mot de passe | Bearer |

#### Détails clés

**`POST /auth/login`**
- Request : `{ "telephone": "+229...", "password": "..." }`
- Response 200 : `TokenResponse` (access + refresh + expires_in)
- Errors : 401 (mauvais identifiants), 403 (compte suspendu), 429 (trop de tentatives)
- Rate limit : 10/min/IP

**`POST /auth/otp/verify`**
- Request : `{ "telephone": "+229...", "code": "1234" }`
- Response 200 : `{ "verified": true }` + activation du flag `telephone_verifie`
- Errors : 400 (code expiré ou invalide), 429 (trop de tentatives)

### 8.2 Utilisateurs — `/users`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `GET` | `/users/me` | Mon profil | Bearer |
| `PATCH` | `/users/me` | Modifier mon profil | Bearer |
| `POST` | `/users/me/photo` | Upload photo profil (multipart) | Bearer |
| `DELETE` | `/users/me` | Supprimer mon compte (soft delete) | Bearer |
| `POST` | `/users/me/fcm-token` | Enregistrer token push | Bearer |
| `GET` | `/users/me/avis` | Avis reçus me concernant | Bearer |
| `GET` | `/users/{user_id}` | Profil public d'un utilisateur | Bearer |

### 8.3 Chauffeurs — `/chauffeurs`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `GET` | `/chauffeurs/me` | Mon profil chauffeur (KYC, véhicules, stats) | Chauffeur |
| `PATCH` | `/chauffeurs/me` | Modifier infos chauffeur | Chauffeur |
| `POST` | `/chauffeurs/me/documents` | Upload pièces KYC | Chauffeur |
| `POST` | `/chauffeurs/me/online` | Passer en ligne (toggle disponibilité) | Chauffeur |
| `POST` | `/chauffeurs/me/offline` | Passer hors ligne | Chauffeur |
| `POST` | `/chauffeurs/me/position` | Mettre à jour position GPS | Chauffeur |
| `GET` | `/chauffeurs/me/revenus` | Revenus jour/semaine/mois | Chauffeur |
| `GET` | `/chauffeurs/me/stats` | Statistiques (trajets, note, courses) | Chauffeur |
| `GET` | `/chauffeurs/me/vehicules` | Mes véhicules | Chauffeur |
| `POST` | `/chauffeurs/me/vehicules` | Ajouter un véhicule | Chauffeur |
| `PATCH` | `/chauffeurs/me/vehicules/{id}` | Modifier un véhicule | Chauffeur |
| `DELETE` | `/chauffeurs/me/vehicules/{id}` | Supprimer un véhicule | Chauffeur |
| `GET` | `/chauffeurs/{id}` | Profil public chauffeur | Bearer |
| `GET` | `/chauffeurs/{id}/voyages` | Voyages publiés par ce chauffeur | Bearer |

#### Détails clés

**`POST /chauffeurs/me/position`**
- Request : `{ "lat": 6.3703, "lng": 2.3912, "vitesse": 68, "heading": 45 }`
- Response 204 (pas de contenu)
- Side effects : update `derniere_position_*`, broadcast WebSocket `tracking:{voyage_id}`
- Rate limit : 1 req/3 sec/chauffeur

### 8.4 Voyages — `/voyages`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `POST` | `/voyages` | Publier un trajet | Chauffeur |
| `GET` | `/voyages/search` | Rechercher trajets dispos | Bearer |
| `GET` | `/voyages/popular` | Trajets populaires (page d'accueil) | Public |
| `GET` | `/voyages/me` | Mes voyages publiés (chauffeur) | Chauffeur |
| `GET` | `/voyages/{id}` | Détail d'un voyage | Bearer |
| `PATCH` | `/voyages/{id}` | Modifier un voyage (avant départ) | Chauffeur (owner) |
| `POST` | `/voyages/{id}/start` | Démarrer le trajet | Chauffeur (owner) |
| `POST` | `/voyages/{id}/end` | Terminer le trajet | Chauffeur (owner) |
| `POST` | `/voyages/{id}/cancel` | Annuler le trajet | Chauffeur (owner) |
| `GET` | `/voyages/{id}/passagers` | Liste des passagers | Chauffeur (owner) |
| `GET` | `/voyages/{id}/tracking` | Position GPS live | Bearer (passager) |

#### Détails clés

**`GET /voyages/search`**
- Query params : `ville_depart, ville_arrivee, date_depart, nombre_places, accepte_colis, climatise, prix_max, sort_by`
- Response 200 : `PaginatedResponse[VoyageRead]`
- Filtres possibles : prix, climatisation, note minimale du chauffeur, durée estimée
- Tri : `prix_asc`, `prix_desc`, `note_desc`, `depart_asc`

**`POST /voyages`**
- Request : `VoyageCreate`
- Response 201 : `VoyageRead`
- Validation : chauffeur doit avoir KYC validé + véhicule actif + être en ligne
- Side effects : calcul distance/ETA via Google Maps Distance Matrix

### 8.5 Réservations — `/reservations`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `POST` | `/reservations` | Créer une réservation | Client |
| `GET` | `/reservations/me` | Mes réservations | Bearer |
| `GET` | `/reservations/{id}` | Détail d'une réservation | Bearer (owner ou chauffeur) |
| `POST` | `/reservations/{id}/accept` | Accepter (chauffeur) | Chauffeur |
| `POST` | `/reservations/{id}/reject` | Refuser (chauffeur) | Chauffeur |
| `POST` | `/reservations/{id}/cancel` | Annuler (client ou chauffeur) | Bearer (owner) |
| `POST` | `/reservations/{id}/pay` | Initier paiement | Client |
| `GET` | `/reservations/me/incoming` | Réservations à valider (chauffeur) | Chauffeur |

#### Workflow détaillé

```
EN_ATTENTE
    ├─ accept (chauffeur) → CONFIRMEE
    ├─ reject (chauffeur) → REFUSEE
    └─ cancel (client)    → ANNULEE

CONFIRMEE
    ├─ pay (client)       → CONFIRMEE + paiement réussi
    ├─ cancel             → ANNULEE (remboursement si payé)
    └─ voyage terminé     → TERMINEE
```

### 8.6 Colis — `/colis`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `POST` | `/colis` | Créer une demande d'envoi | Client |
| `POST` | `/colis/estimate` | Estimer prix d'un envoi | Bearer |
| `GET` | `/colis/me` | Mes colis (envoyés/reçus) | Bearer |
| `GET` | `/colis/me/transports` | Colis que je transporte (chauffeur) | Chauffeur |
| `GET` | `/colis/{id}` | Détail d'un colis | Bearer (owner/chauffeur/admin) |
| `GET` | `/colis/{ref}/track` | Suivi public (avec référence) | Public |
| `POST` | `/colis/{id}/photo` | Ajouter photo | Client (owner) |
| `POST` | `/colis/{id}/cancel` | Annuler la demande | Client (owner) |
| `POST` | `/colis/{id}/pickup` | Confirmer récupération (chauffeur) | Chauffeur |
| `POST` | `/colis/{id}/in-transit` | Marquer en route | Chauffeur |
| `POST` | `/colis/{id}/deliver` | Marquer livré (avec code retrait) | Chauffeur |
| `POST` | `/colis/{id}/dispute` | Ouvrir un litige | Bearer |

#### Détails clés

**`POST /colis`**
- Request : `ColisCreate` (type, poids, description, adresses, destinataire, etc.)
- Response 201 : `ColisRead` avec `reference` (ex: `GT-2026-04-8721`) + `code_retrait`
- Side effects :
  - Création entrée `SuiviColis` initiale
  - Notification push admin (à valider)
  - SMS au destinataire avec référence et code retrait

**`POST /colis/{id}/deliver`**
- Request : `{ "code_retrait": "1234", "signature_url": "...", "photo_url": "..." }`
- Validation : le code doit matcher exactement
- Response 200 : `ColisRead` mis à jour
- Side effects :
  - Création entrée `SuiviColis` finale
  - Crédit du chauffeur dans son wallet (montant - commission)
  - Notification push à l'expéditeur
  - SMS au destinataire confirmant la livraison

### 8.7 Suivi temps réel — `/suivi`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `GET` | `/suivi/voyage/{id}` | Position chauffeur + ETA | Bearer (passager) |
| `GET` | `/suivi/colis/{id}` | Historique + position actuelle | Bearer |
| `GET` | `/suivi/colis/{ref}/public` | Suivi public via référence | Public |
| `WS` | `/ws/tracking/voyage/{id}` | WebSocket position chauffeur | Bearer (passager) |
| `WS` | `/ws/tracking/colis/{id}` | WebSocket suivi colis | Bearer |
| `WS` | `/ws/notifications` | Notifications push live | Bearer |

### 8.8 Wallet — `/wallet`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `GET` | `/wallet/me` | Mon solde + stats | Bearer |
| `GET` | `/wallet/me/activity` | Activité récente (paginée) | Bearer |
| `POST` | `/wallet/me/recharge/initiate` | Initier recharge MoMo | Bearer |
| `POST` | `/wallet/me/recharge/confirm` | Confirmer après USSD | Bearer |
| `POST` | `/wallet/me/withdraw` | Retrait vers MoMo (chauffeur) | Chauffeur |
| `POST` | `/wallet/me/transfer` | Transfert wallet → wallet | Bearer |

### 8.9 Transactions — `/transactions`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `GET` | `/transactions/me` | Mes transactions (paginées + filtres) | Bearer |
| `GET` | `/transactions/{id}` | Détail d'une transaction | Bearer (owner) |
| `GET` | `/transactions/{id}/receipt` | Reçu PDF | Bearer (owner) |

### 8.10 Webhooks Mobile Money — `/webhooks`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `POST` | `/webhooks/momo/mtn` | Callback MTN MoMo | Signature MTN |
| `POST` | `/webhooks/momo/moov` | Callback Moov | Signature Moov |
| `POST` | `/webhooks/momo/orange` | Callback Orange | Signature Orange |

> **⚠️ Sécurité :** Tous les webhooks vérifient signature HMAC + IP whitelist + idempotency key.

### 8.11 Avis — `/avis`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `POST` | `/avis` | Publier un avis post-trajet | Client |
| `GET` | `/avis/chauffeur/{id}` | Avis d'un chauffeur (paginés) | Public |
| `GET` | `/avis/me/recus` | Mes avis reçus | Bearer |
| `POST` | `/avis/{id}/signaler` | Signaler un avis | Bearer |

### 8.12 Notifications — `/notifications`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `GET` | `/notifications/me` | Mes notifications (paginées) | Bearer |
| `POST` | `/notifications/me/read-all` | Marquer toutes lues | Bearer |
| `POST` | `/notifications/{id}/read` | Marquer une lue | Bearer |
| `DELETE` | `/notifications/{id}` | Supprimer | Bearer |
| `GET` | `/notifications/me/unread-count` | Compteur non lues | Bearer |

### 8.13 Public — `/public`

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `GET` | `/public/villes` | Liste villes desservies | Public |
| `GET` | `/public/trajets-populaires` | Trajets populaires (landing) | Public |
| `GET` | `/public/stats` | Stats publiques (50K trajets, etc.) | Public |
| `GET` | `/public/health` | Health check | Public |

### 8.14 Admin — `/admin`

#### Vue d'ensemble & analytics

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `GET` | `/admin/dashboard/overview` | KPIs principaux | ADMIN |
| `GET` | `/admin/dashboard/revenus` | Évolution revenus 7j/30j/90j | ADMIN |
| `GET` | `/admin/dashboard/top-trajets` | Top trajets populaires | ADMIN |
| `GET` | `/admin/dashboard/activity-feed` | Activité live | ADMIN |
| `GET` | `/admin/dashboard/momo-stats` | Répartition Mobile Money | ADMIN |
| `GET` | `/admin/dashboard/fleet-map` | Données carte temps réel flotte | ADMIN |

#### Utilisateurs

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `GET` | `/admin/users` | Liste utilisateurs (filtres + pagination) | ADMIN |
| `GET` | `/admin/users/{id}` | Détail utilisateur | ADMIN |
| `POST` | `/admin/users/{id}/suspend` | Suspendre | ADMIN |
| `POST` | `/admin/users/{id}/activate` | Réactiver | ADMIN |
| `POST` | `/admin/users/{id}/note` | Ajouter note interne | ADMIN |

#### Chauffeurs / KYC

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `GET` | `/admin/chauffeurs/pending` | KYC en attente | ADMIN |
| `POST` | `/admin/chauffeurs/{id}/approve-kyc` | Valider KYC | ADMIN |
| `POST` | `/admin/chauffeurs/{id}/reject-kyc` | Rejeter KYC | ADMIN |
| `POST` | `/admin/chauffeurs/{id}/transborder` | Activer autorisation transfrontalière | ADMIN |

#### Voyages

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `GET` | `/admin/voyages` | Liste voyages (filtres) | ADMIN |
| `GET` | `/admin/voyages/{id}` | Détail (passagers, colis, GPS) | ADMIN |
| `POST` | `/admin/voyages/{id}/cancel` | Forcer annulation | ADMIN |
| `POST` | `/admin/voyages/{id}/end` | Forcer fin de trajet | ADMIN |

#### Colis

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `GET` | `/admin/colis/pending` | Demandes à valider | ADMIN |
| `POST` | `/admin/colis/{id}/validate` | Valider la demande | ADMIN |
| `POST` | `/admin/colis/{id}/reject` | Refuser | ADMIN |
| `POST` | `/admin/colis/{id}/assign` | Assigner à un chauffeur | ADMIN |
| `POST` | `/admin/colis/{id}/auto-assign` | Assignation auto (algorithme) | ADMIN |
| `GET` | `/admin/colis/in-transit` | Colis en route (temps réel) | ADMIN |

#### Transactions

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `GET` | `/admin/transactions` | Toutes les transactions (filtres) | ADMIN |
| `GET` | `/admin/transactions/failed` | Échecs à investiguer | ADMIN |
| `POST` | `/admin/transactions/{id}/refund` | Forcer remboursement | SUPER_ADMIN |
| `GET` | `/admin/transactions/export` | Export CSV (rapport BCEAO) | SUPER_ADMIN |
| `GET` | `/admin/transactions/operators-status` | Status APIs MoMo | ADMIN |

#### Avis & litiges

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `GET` | `/admin/avis/signales` | Avis signalés | ADMIN |
| `POST` | `/admin/avis/{id}/keep` | Maintenir | ADMIN |
| `POST` | `/admin/avis/{id}/delete` | Supprimer | ADMIN |
| `GET` | `/admin/litiges` | Litiges ouverts | ADMIN |
| `POST` | `/admin/litiges/{id}/arbitrate` | Arbitrer | ADMIN |

#### Audit

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `GET` | `/admin/audit/logs` | Logs d'audit (paginés + filtres) | SUPER_ADMIN |
| `GET` | `/admin/audit/sessions` | Sessions admin actives | SUPER_ADMIN |

### 8.15 Codes d'erreur standardisés

```python
# app/exceptions.py
class GoTaxiException(Exception):
    code: str
    message: str
    status_code: int = 400

class UserNotFoundException(GoTaxiException):
    code = "USER_NOT_FOUND"
    status_code = 404

class InvalidOTPException(GoTaxiException):
    code = "INVALID_OTP"
    status_code = 400

class InsufficientFundsException(GoTaxiException):
    code = "INSUFFICIENT_FUNDS"
    status_code = 402

class VoyageFullException(GoTaxiException):
    code = "VOYAGE_FULL"
    status_code = 409
# ... etc
```

Format réponse erreur :
```json
{
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Solde wallet insuffisant",
    "details": { "solde_actuel": 500, "montant_requis": 8500 },
    "request_id": "req_abc123"
  }
}
```

---

## 9. WebSockets & temps réel

### 9.1 Manager de connexions

```python
# app/websockets/manager.py
from collections import defaultdict
from fastapi import WebSocket
from uuid import UUID


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self._connections[channel].add(ws)

    def disconnect(self, channel: str, ws: WebSocket):
        self._connections[channel].discard(ws)
        if not self._connections[channel]:
            del self._connections[channel]

    async def broadcast(self, channel: str, message: dict):
        for ws in self._connections.get(channel, set()).copy():
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(channel, ws)


manager = ConnectionManager()
```

### 9.2 Routeur WebSocket tracking

```python
# app/websockets/tracking.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websockets.manager import manager
from app.dependencies import get_current_user_ws  # version WS

router = APIRouter()


@router.websocket("/ws/tracking/voyage/{voyage_id}")
async def tracking_voyage(
    ws: WebSocket,
    voyage_id: UUID,
    user = Depends(get_current_user_ws),
):
    channel = f"tracking:voyage:{voyage_id}"
    await manager.connect(channel, ws)
    try:
        while True:
            await ws.receive_text()  # heartbeat client
    except WebSocketDisconnect:
        manager.disconnect(channel, ws)
```

### 9.3 Format des messages WS

```json
// Position chauffeur
{
  "type": "position_update",
  "voyage_id": "...",
  "lat": 6.3703,
  "lng": 2.3912,
  "vitesse": 68,
  "heading": 45,
  "timestamp": "2026-04-26T14:23:00Z"
}

// Changement statut colis
{
  "type": "colis_status_update",
  "colis_id": "...",
  "statut": "EN_ROUTE",
  "ville": "Bohicon",
  "eta": "2026-04-26T16:42:00Z",
  "timestamp": "..."
}

// Notification push
{
  "type": "notification",
  "title": "Nouvelle réservation",
  "body": "Marie S. veut réserver 2 places...",
  "data": { "reservation_id": "..." }
}
```

---

## 10. Intégrations externes

### 10.1 Mobile Money MTN

```python
# app/integrations/mtn_momo.py
import httpx
from uuid import uuid4
from app.config import get_settings

settings = get_settings()


class MTNMoMoClient:
    def __init__(self):
        self.base_url = settings.MTN_MOMO_API_URL
        self.subscription_key = settings.MTN_MOMO_SUBSCRIPTION_KEY

    async def _get_access_token(self) -> str:
        # Implémentation OAuth2 client_credentials
        ...

    async def request_to_pay(
        self,
        amount: int,
        phone: str,
        external_id: str,
    ) -> str:
        """Initie un paiement MoMo. Retourne reference_id."""
        token = await self._get_access_token()
        reference_id = str(uuid4())
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/collection/v1_0/requesttopay",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Reference-Id": reference_id,
                    "X-Target-Environment": settings.MTN_MOMO_TARGET_ENV,
                    "Ocp-Apim-Subscription-Key": self.subscription_key,
                },
                json={
                    "amount": str(amount),
                    "currency": "XOF",
                    "externalId": external_id,
                    "payer": {"partyIdType": "MSISDN", "partyId": phone.replace("+", "")},
                    "payerMessage": "Recharge GoTaxi",
                    "payeeNote": "GoTaxi wallet",
                },
            )
            response.raise_for_status()
            return reference_id

    async def get_transaction_status(self, reference_id: str) -> dict:
        ...
```

### 10.2 Firebase Cloud Messaging

```python
# app/integrations/fcm.py
import firebase_admin
from firebase_admin import credentials, messaging
from app.config import get_settings

settings = get_settings()
cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)


async def send_push(token: str, title: str, body: str, data: dict = None):
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        token=token,
    )
    return messaging.send(message)
```

### 10.3 Twilio SMS

```python
# app/integrations/twilio_sms.py
from twilio.rest import Client
from app.config import get_settings

settings = get_settings()
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_sms(to: str, body: str):
    return client.messages.create(
        from_=settings.TWILIO_FROM_NUMBER,
        to=to,
        body=body,
    )
```

---

## 11. Tâches asynchrones (Celery)

### 11.1 App Celery

```python
# app/tasks/celery_app.py
from celery import Celery
from app.config import get_settings

settings = get_settings()
celery_app = Celery(
    "gotaxi",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.sms_tasks",
        "app.tasks.push_tasks",
        "app.tasks.payment_tasks",
        "app.tasks.reports_tasks",
    ],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Porto-Novo",
    enable_utc=True,
    beat_schedule={
        "check-pending-payments": {
            "task": "app.tasks.payment_tasks.check_pending_momo",
            "schedule": 60.0,  # toutes les 60 sec
        },
        "send-daily-reports": {
            "task": "app.tasks.reports_tasks.send_daily_admin_report",
            "schedule": "0 8 * * *",  # tous les jours à 8h
        },
    },
)
```

### 11.2 Exemples de tâches

```python
# app/tasks/sms_tasks.py
@celery_app.task(bind=True, max_retries=3)
def send_otp_sms(self, telephone: str, code: str):
    try:
        send_sms(telephone, f"GoTaxi : votre code est {code}. Valide 5 min.")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# app/tasks/payment_tasks.py
@celery_app.task
def check_pending_momo():
    """Vérifie le statut des paiements MoMo en attente."""
    ...


@celery_app.task
def process_chauffeur_payout(chauffeur_id: str, amount: int):
    """Traite le reversement vers MoMo du chauffeur."""
    ...


# app/tasks/reports_tasks.py
@celery_app.task
def send_daily_admin_report():
    """Génère et envoie le rapport quotidien aux admins."""
    ...
```

---

## 12. Tests

### 12.1 Configuration pytest

```python
# tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.core.database import get_db
from tests.factories import UserFactory


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def auth_headers(async_client, db_session):
    user = await UserFactory.create(db_session)
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"telephone": user.telephone, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### 12.2 Test d'endpoint

```python
# tests/integration/test_voyages.py
import pytest


@pytest.mark.asyncio
async def test_search_voyages(async_client, auth_headers):
    response = await async_client.get(
        "/api/v1/voyages/search",
        params={
            "ville_depart": "Cotonou",
            "ville_arrivee": "Parakou",
            "date_depart": "2026-04-28",
            "nombre_places": 2,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "items" in response.json()
```

### 12.3 Couverture cible

- **Unitaires :** 90%+ sur services et utils
- **Intégration :** 100% des endpoints critiques (auth, paiement, colis)
- **E2E :** scénarios principaux (réservation complète, envoi colis bout en bout)

---

## 13. Déploiement & DevOps

### 13.1 Dockerfile

```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 13.2 docker-compose.yml (dev)

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis]
    volumes: [".:/app"]
    command: uvicorn app.main:app --reload --host 0.0.0.0

  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_USER: gotaxi
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: gotaxi
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  celery_worker:
    build: .
    command: celery -A app.tasks.celery_app worker --loglevel=info
    env_file: .env
    depends_on: [redis, postgres]

  celery_beat:
    build: .
    command: celery -A app.tasks.celery_app beat --loglevel=info
    env_file: .env
    depends_on: [redis]

volumes:
  postgres_data:
```

### 13.3 Production checklist

- [ ] HTTPS partout (Let's Encrypt + nginx reverse proxy)
- [ ] Secrets dans vault (HashiCorp Vault ou AWS Secrets Manager)
- [ ] Base de données managée (RDS PostgreSQL avec replicas read-only)
- [ ] Redis managé (ElastiCache ou Upstash)
- [ ] CDN pour les uploads (CloudFront + S3)
- [ ] Monitoring : Prometheus + Grafana + Sentry
- [ ] Logs centralisés (ELK ou Loki)
- [ ] Backup DB quotidien + test de restore mensuel
- [ ] Rate limiting (slowapi ou nginx)
- [ ] Health checks `/public/health` + `/public/health/db`
- [ ] CORS strict (uniquement domaines GoTaxi)
- [ ] CSP headers
- [ ] Audit logs immutables (write-once)
- [ ] Rotation des clés JWT tous les 90 jours

### 13.4 CI/CD (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:16-3.4
        env: { POSTGRES_PASSWORD: test }
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy app/
      - run: pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v4
```

---

## 14. Conventions de code

### 14.1 Style

- **PEP 8** strict, vérifié par `ruff`
- **Type hints** obligatoires, vérifiés par `mypy --strict`
- **Docstrings** style Google sur toutes les fonctions publiques
- **Imports** triés (`isort` via `ruff`)
- **Longueur de ligne** : 100 caractères max

### 14.2 Nommage

- `snake_case` pour fichiers, fonctions, variables
- `PascalCase` pour classes
- `UPPER_SNAKE_CASE` pour constantes
- Enums en français (cohérence métier) : `EN_ATTENTE`, `CONFIRMEE`, etc.
- Suffixes Pydantic : `Create`, `Update`, `Read`

### 14.3 Git

- Branches : `feat/...`, `fix/...`, `chore/...`, `docs/...`
- Commits : Conventional Commits (`feat: ajouter endpoint colis`)
- Merge : squash + merge sur `main`
- PRs : minimum 1 reviewer, CI verte obligatoire

### 14.4 Documentation

- README à jour
- Changelog suivant Keep a Changelog
- Doc API : auto-générée par FastAPI sur `/docs` et `/redoc`
- ADR (Architectural Decision Records) dans `docs/adr/`

---

## 🎯 Roadmap d'implémentation suggérée

### Sprint 1 (semaine 1-2) — Fondations
- Setup projet, structure, Docker
- Modèles + migrations Alembic
- Auth complète (register, login, OTP, JWT)
- Endpoints `/users/me`, `/chauffeurs/me`

### Sprint 2 (semaine 3-4) — Voyages & réservations
- CRUD voyages
- Recherche avec filtres
- Workflow réservation complet
- Tests intégration

### Sprint 3 (semaine 5-6) — Colis
- Création + workflow validation/assignation
- Suivi (timeline)
- Endpoints chauffeur (pickup, deliver)

### Sprint 4 (semaine 7) — Wallet & Mobile Money
- Wallet + transactions
- Intégration MTN MoMo (sandbox d'abord)
- Webhooks + Celery

### Sprint 5 (semaine 8) — Temps réel
- WebSockets tracking
- Notifications push (FCM)
- Activité live admin

### Sprint 6 (semaine 9) — Admin
- Dashboard endpoints
- Modération colis & avis
- Audit logs

### Sprint 7 (semaine 10) — Hardening
- Tests E2E
- Rate limiting
- Monitoring + alerting
- Sécurité review
- Documentation finale

---

**Fin du guide backend.** Pour la stack mobile, voir `MOBILE_REACT_NATIVE.md`. Pour le web, voir `WEB_REACT_JS.md`.
