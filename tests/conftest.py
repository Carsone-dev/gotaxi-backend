import asyncio
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from sqlalchemy import delete, select, insert as sa_insert, update as sa_update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# ── 1. Patch DB (NullPool) avant tout import de app ──────────────────────────
from app.config import get_settings
from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus
from app.models.chauffeur import Chauffeur
from app.models.vehicule import Vehicule
from app.models.voyage import Voyage
from app.models.reservation import Reservation
import app.core.database as _db_mod

settings = get_settings()

_null_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
_db_mod.AsyncSessionLocal = async_sessionmaker(
    _null_engine, class_=AsyncSession, expire_on_commit=False
)

# ── 2. Import app APRÈS le patch ─────────────────────────────────────────────
from httpx import AsyncClient, ASGITransport  # noqa: E402
from app.main import app  # noqa: E402

import app.core.redis_client as _redis_mod  # noqa: E402

TEST_PHONE = "+2290100000001"
TEST_PHONE_2 = "+2290100000002"
TEST_ADMIN_PHONE = "+2290100000020"


def _new_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)


@pytest.fixture(autouse=True)
def reset_redis():
    _redis_mod.redis_client = _new_redis()
    yield


@pytest.fixture(autouse=True)
def cleanup(reset_redis):
    yield
    async def _run():
        engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        async with engine.begin() as conn:
            result = await conn.execute(
                select(User.id).where(User.telephone.in_([TEST_PHONE, TEST_PHONE_2]))
            )
            user_ids = [row[0] for row in result.fetchall()]

            if user_ids:
                result = await conn.execute(
                    select(Chauffeur.id).where(Chauffeur.user_id.in_(user_ids))
                )
                chauffeur_ids = [row[0] for row in result.fetchall()]

                if chauffeur_ids:
                    result = await conn.execute(
                        select(Voyage.id).where(Voyage.chauffeur_id.in_(chauffeur_ids))
                    )
                    voyage_ids = [row[0] for row in result.fetchall()]

                    if voyage_ids:
                        await conn.execute(
                            delete(Reservation).where(Reservation.voyage_id.in_(voyage_ids))
                        )
                    # Réservations faites par ces utilisateurs (client)
                    await conn.execute(
                        delete(Reservation).where(Reservation.client_id.in_(user_ids))
                    )
                    await conn.execute(
                        delete(Voyage).where(Voyage.chauffeur_id.in_(chauffeur_ids))
                    )
                    await conn.execute(
                        delete(Vehicule).where(Vehicule.chauffeur_id.in_(chauffeur_ids))
                    )
                await conn.execute(
                    delete(Chauffeur).where(Chauffeur.user_id.in_(user_ids))
                )

            await conn.execute(
                delete(User).where(User.telephone.in_([TEST_PHONE, TEST_PHONE_2, TEST_ADMIN_PHONE]))
            )
        await engine.dispose()

        redis = _new_redis()
        for phone in [TEST_PHONE, TEST_PHONE_2, TEST_ADMIN_PHONE]:
            await redis.delete(f"otp:{phone}", f"otp_lock:{phone}")
        await redis.aclose()
    asyncio.run(_run())


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "telephone": TEST_PHONE,
        "nom": "Test",
        "prenom": "User",
        "password": "motdepasse123",
    })
    return {"telephone": TEST_PHONE, "password": "motdepasse123"}


@pytest_asyncio.fixture
async def auth_tokens(client: AsyncClient, registered_user: dict):
    resp = await client.post("/api/v1/auth/login", json=registered_user)
    return resp.json()


@pytest_asyncio.fixture
async def chauffeur_user(client: AsyncClient):
    """Crée un utilisateur avec rôle CHAUFFEUR et un profil chauffeur (KYC validé)."""
    await client.post("/api/v1/auth/register", json={
        "telephone": TEST_PHONE_2,
        "nom": "Dupont",
        "prenom": "Marc",
        "password": "motdepasse123",
    })

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        result = await conn.execute(
            select(User.id).where(User.telephone == TEST_PHONE_2)
        )
        user_id = result.scalar_one()

        await conn.execute(
            sa_update(User).where(User.id == user_id).values(role="CHAUFFEUR")
        )

        await conn.execute(
            sa_insert(Chauffeur).values(
                id=uuid4(),
                user_id=user_id,
                cin_numero="BE1234567",
                cin_url="http://example.com/cin.jpg",
                permis_numero="P987654",
                permis_url="http://example.com/permis.jpg",
                permis_expiration=date(2028, 1, 1),
                casier_judiciaire_url=None,
                kyc_valide=True,
                kyc_valide_le=date.today(),
                autorisation_transfrontaliere=False,
                en_ligne=False,
                nombre_trajets=0,
                revenus_total=0,
            )
        )
    await engine.dispose()

    return {"telephone": TEST_PHONE_2, "password": "motdepasse123"}


@pytest_asyncio.fixture
async def chauffeur_auth_tokens(client: AsyncClient, chauffeur_user: dict):
    resp = await client.post("/api/v1/auth/login", json=chauffeur_user)
    return resp.json()


@pytest_asyncio.fixture
async def admin_user():
    """Crée un utilisateur ADMIN directement en base (sans passer par l'API)."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            sa_insert(User).values(
                id=uuid4(),
                telephone=TEST_ADMIN_PHONE,
                email=None,
                nom="Admin",
                prenom="Test",
                password_hash=hash_password("Admin@test123!"),
                role=UserRole.ADMIN,
                statut=UserStatus.ACTIF,
                telephone_verifie=True,
                email_verifie=False,
                note_moyenne=0,
                nombre_avis=0,
                langue="fr",
            )
        )
    await engine.dispose()
    return {"telephone": TEST_ADMIN_PHONE, "password": "Admin@test123!"}


@pytest_asyncio.fixture
async def admin_auth_tokens(client: AsyncClient, admin_user: dict):
    resp = await client.post("/api/v1/auth/login", json=admin_user)
    return resp.json()


@pytest_asyncio.fixture
async def voyage(client: AsyncClient, chauffeur_auth_tokens: dict):
    """Crée un véhicule + passe en ligne + crée un voyage. Retourne les données du voyage."""
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}

    # Passer en ligne
    await client.post("/api/v1/chauffeurs/me/online", headers=headers)

    # Créer un véhicule
    veh_resp = await client.post("/api/v1/chauffeurs/me/vehicules", headers=headers, json={
        "marque": "Toyota",
        "modele": "Corolla",
        "annee": 2020,
        "immatriculation": "BJ-TEST-01",
        "couleur": "Blanc",
        "type_vehicule": "BERLINE",
        "nombre_places": 4,
        "climatise": True,
    })
    vehicule_id = veh_resp.json()["id"]

    # Créer un voyage dans 2 heures
    date_depart = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    voyage_resp = await client.post("/api/v1/voyages", headers=headers, json={
        "ville_depart": "Cotonou",
        "ville_arrivee": "Parakou",
        "point_depart": "Gare de Cotonou",
        "point_arrivee": "Gare de Parakou",
        "lat_depart": 6.3703,
        "lng_depart": 2.3912,
        "lat_arrivee": 9.3372,
        "lng_arrivee": 2.6281,
        "date_depart": date_depart,
        "prix_par_place": 5000,
        "nombre_places_total": 4,
        "climatise": True,
        "vehicule_id": vehicule_id,
    })
    assert voyage_resp.status_code == 201, voyage_resp.text
    return voyage_resp.json()