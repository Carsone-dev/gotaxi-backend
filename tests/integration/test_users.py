import pytest
from httpx import AsyncClient

from tests.conftest import TEST_PHONE


# ── GET /users/me ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["telephone"] == TEST_PHONE
    assert data["nom"] == "Test"
    assert data["prenom"] == "User"
    assert data["role"] == "CLIENT"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


# ── PATCH /users/me ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_me(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.patch("/api/v1/users/me", headers=headers, json={
        "nom": "NouveauNom",
        "prenom": "NouveauPrenom",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["nom"] == "NouveauNom"
    assert data["prenom"] == "NouveauPrenom"

    # Vérifier persistance en rechargeant le profil
    resp2 = await client.get("/api/v1/users/me", headers=headers)
    assert resp2.json()["nom"] == "NouveauNom"


@pytest.mark.asyncio
async def test_update_me_partial(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.patch("/api/v1/users/me", headers=headers, json={
        "langue": "en",
    })
    assert resp.status_code == 200
    assert resp.json()["langue"] == "en"
    assert resp.json()["nom"] == "Test"  # non modifié


@pytest.mark.asyncio
async def test_update_me_email(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.patch("/api/v1/users/me", headers=headers, json={
        "email": "test@example.com",
    })
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


# ── POST /users/me/fcm-token ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fcm_token(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.post(
        "/api/v1/users/me/fcm-token",
        headers=headers,
        params={"token": "fcm_token_abc123"},
    )
    assert resp.status_code == 200
    assert "FCM" in resp.json()["message"]


# ── DELETE /users/me ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_me(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.delete("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200

    # Après suppression, le token est invalide (user SUPPRIME)
    resp2 = await client.get("/api/v1/users/me", headers=headers)
    assert resp2.status_code == 401


# ── GET /users/{user_id} ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_public(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}

    # Récupérer son propre profil d'abord
    me_resp = await client.get("/api/v1/users/me", headers=headers)
    user_id = me_resp.json()["id"]

    resp = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == user_id
    assert "nom" in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_get_user_public_unknown(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


# ── GET /users/me/avis ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_my_avis_empty(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.get("/api/v1/users/me/avis", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []