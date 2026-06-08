import pytest
from httpx import AsyncClient

from tests.conftest import TEST_PHONE_2


# ── GET /chauffeurs/me ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_chauffeur_profile(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    resp = await client.get("/api/v1/chauffeurs/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["cin_numero"] == "BE1234567"
    assert data["kyc_valide"] is True
    assert data["vehicules"] == []


@pytest.mark.asyncio
async def test_get_chauffeur_profile_requires_chauffeur_role(
    client: AsyncClient, auth_tokens: dict
):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.get("/api/v1/chauffeurs/me", headers=headers)
    assert resp.status_code == 403


# ── PATCH /chauffeurs/me ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_chauffeur_profile(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    resp = await client.patch("/api/v1/chauffeurs/me", headers=headers, json={
        "cin_numero": "BJ9999999",
    })
    assert resp.status_code == 200
    assert resp.json()["cin_numero"] == "BJ9999999"

    # Vérifier persistance
    resp2 = await client.get("/api/v1/chauffeurs/me", headers=headers)
    assert resp2.json()["cin_numero"] == "BJ9999999"


# ── POST /chauffeurs/me/online & offline ──────────────────────────────────────

@pytest.mark.asyncio
async def test_go_online_offline(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}

    # Passer en ligne
    resp = await client.post("/api/v1/chauffeurs/me/online", headers=headers)
    assert resp.status_code == 200
    assert "en ligne" in resp.json()["message"]

    # Vérifier état
    profile = await client.get("/api/v1/chauffeurs/me", headers=headers)
    assert profile.json()["en_ligne"] is True

    # Passer hors ligne
    resp2 = await client.post("/api/v1/chauffeurs/me/offline", headers=headers)
    assert resp2.status_code == 200

    profile2 = await client.get("/api/v1/chauffeurs/me", headers=headers)
    assert profile2.json()["en_ligne"] is False


@pytest.mark.asyncio
async def test_go_online_kyc_not_validated(
    client: AsyncClient, chauffeur_auth_tokens: dict
):
    """Un chauffeur avec KYC non validé ne peut pas passer en ligne."""
    from sqlalchemy import update as sa_update
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from app.config import get_settings
    from app.models.chauffeur import Chauffeur as ChauffeurModel
    from app.models.user import User

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        from sqlalchemy import select
        result = await conn.execute(
            select(User.id).where(User.telephone == TEST_PHONE_2)
        )
        user_id = result.scalar_one()
        await conn.execute(
            sa_update(ChauffeurModel)
            .where(ChauffeurModel.user_id == user_id)
            .values(kyc_valide=False)
        )
    await engine.dispose()

    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    resp = await client.post("/api/v1/chauffeurs/me/online", headers=headers)
    assert resp.status_code == 403


# ── POST /chauffeurs/me/position ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_position(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    resp = await client.post("/api/v1/chauffeurs/me/position", headers=headers, json={
        "lat": 6.3703,
        "lng": 2.3912,
        "vitesse": 60.0,
        "heading": 90.0,
    })
    assert resp.status_code == 204

    # Vérifier la mise à jour
    profile = await client.get("/api/v1/chauffeurs/me", headers=headers)
    data = profile.json()
    assert abs(float(data["derniere_position_lat"]) - 6.3703) < 0.001
    assert abs(float(data["derniere_position_lng"]) - 2.3912) < 0.001


@pytest.mark.asyncio
async def test_update_position_invalid(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    resp = await client.post("/api/v1/chauffeurs/me/position", headers=headers, json={
        "lat": 999,  # hors limites
        "lng": 2.3912,
    })
    assert resp.status_code == 422


# ── GET /chauffeurs/me/stats & revenus ────────────────────────────────────────

@pytest.mark.asyncio
async def test_my_stats(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    resp = await client.get("/api/v1/chauffeurs/me/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "nombre_trajets" in data
    assert "note_moyenne" in data
    assert "en_ligne" in data


@pytest.mark.asyncio
async def test_my_revenus(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    resp = await client.get("/api/v1/chauffeurs/me/revenus", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "aujourd_hui" in data
    assert "semaine" in data
    assert "mois" in data
    assert "total" in data


# ── Véhicules ─────────────────────────────────────────────────────────────────

VEHICULE_PAYLOAD = {
    "marque": "Toyota",
    "modele": "Corolla",
    "annee": 2020,
    "immatriculation": "BJ-1234-A",
    "couleur": "Blanc",
    "type_vehicule": "BERLINE",
    "nombre_places": 4,
    "climatise": True,
}


@pytest.mark.asyncio
async def test_vehicules_empty(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    resp = await client.get("/api/v1/chauffeurs/me/vehicules", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_add_vehicule(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    resp = await client.post(
        "/api/v1/chauffeurs/me/vehicules", headers=headers, json=VEHICULE_PAYLOAD
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["immatriculation"] == "BJ-1234-A"
    assert data["marque"] == "Toyota"
    assert data["actif"] is True

    # Vérifier qu'il apparaît dans la liste
    list_resp = await client.get("/api/v1/chauffeurs/me/vehicules", headers=headers)
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_add_vehicule_duplicate_immat(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    await client.post("/api/v1/chauffeurs/me/vehicules", headers=headers, json=VEHICULE_PAYLOAD)
    resp = await client.post(
        "/api/v1/chauffeurs/me/vehicules", headers=headers, json=VEHICULE_PAYLOAD
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_vehicule(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    create_resp = await client.post(
        "/api/v1/chauffeurs/me/vehicules", headers=headers, json=VEHICULE_PAYLOAD
    )
    vehicule_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/chauffeurs/me/vehicules/{vehicule_id}",
        headers=headers,
        json={"couleur": "Rouge", "climatise": False},
    )
    assert resp.status_code == 200
    assert resp.json()["couleur"] == "Rouge"
    assert resp.json()["climatise"] is False
    assert resp.json()["marque"] == "Toyota"  # non modifié


@pytest.mark.asyncio
async def test_delete_vehicule(client: AsyncClient, chauffeur_auth_tokens: dict):
    headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    create_resp = await client.post(
        "/api/v1/chauffeurs/me/vehicules", headers=headers, json=VEHICULE_PAYLOAD
    )
    vehicule_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/chauffeurs/me/vehicules/{vehicule_id}", headers=headers
    )
    assert resp.status_code == 200

    # Plus visible dans la liste
    list_resp = await client.get("/api/v1/chauffeurs/me/vehicules", headers=headers)
    ids = [v["id"] for v in list_resp.json()]
    assert vehicule_id not in ids


# ── GET /chauffeurs/{id} ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_chauffeur_public(
    client: AsyncClient, auth_tokens: dict, chauffeur_auth_tokens: dict
):
    # Récupérer l'ID du chauffeur
    ch_headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    profile_resp = await client.get("/api/v1/chauffeurs/me", headers=ch_headers)
    chauffeur_id = profile_resp.json()["id"]

    # Consulter depuis un client normal
    cl_headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.get(f"/api/v1/chauffeurs/{chauffeur_id}", headers=cl_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == chauffeur_id
    assert "nom" in data
    assert "cin_numero" not in data  # données privées cachées


@pytest.mark.asyncio
async def test_get_chauffeur_public_unknown(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.get(
        "/api/v1/chauffeurs/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_chauffeur_voyages(
    client: AsyncClient, auth_tokens: dict, chauffeur_auth_tokens: dict
):
    ch_headers = {"Authorization": f"Bearer {chauffeur_auth_tokens['access_token']}"}
    profile_resp = await client.get("/api/v1/chauffeurs/me", headers=ch_headers)
    chauffeur_id = profile_resp.json()["id"]

    cl_headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.get(f"/api/v1/chauffeurs/{chauffeur_id}/voyages", headers=cl_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)