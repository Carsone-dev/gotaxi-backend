import pytest
from httpx import AsyncClient

import app.core.redis_client as _redis_mod
from tests.conftest import TEST_PHONE, TEST_PHONE_2


# ── Register ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "telephone": TEST_PHONE,
        "nom": "Dupont",
        "prenom": "Jean",
        "password": "motdepasse123",
    })
    assert resp.status_code == 201
    assert "Inscription" in resp.json()["message"]


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient, registered_user: dict):
    resp = await client.post("/api/v1/auth/register", json={
        "telephone": TEST_PHONE,
        "nom": "Autre",
        "prenom": "Autre",
        "password": "motdepasse123",
    })
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "PHONE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_invalid_phone(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "telephone": "0022997000001",
        "nom": "Test",
        "prenom": "User",
        "password": "motdepasse123",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "telephone": TEST_PHONE,
        "nom": "Test",
        "prenom": "User",
        "password": "court",
    })
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, registered_user: dict):
    resp = await client.post("/api/v1/auth/login", json=registered_user)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, registered_user: dict):
    resp = await client.post("/api/v1/auth/login", json={
        "telephone": TEST_PHONE,
        "password": "mauvais_mdp",
    })
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_phone(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "telephone": "+2290100000099",
        "password": "motdepasse123",
    })
    assert resp.status_code == 401


# ── OTP ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_otp_send(client: AsyncClient):
    resp = await client.post("/api/v1/auth/otp/send", json={"telephone": TEST_PHONE})
    assert resp.status_code == 200
    assert "OTP" in resp.json()["message"]


@pytest.mark.asyncio
async def test_otp_verify_success(client: AsyncClient, registered_user: dict):
    code = await _redis_mod.redis_client.set(f"otp:{TEST_PHONE}", "123456:0", ex=300)
    resp = await client.post("/api/v1/auth/otp/verify", json={
        "telephone": TEST_PHONE,
        "code": "123456",
    })
    assert resp.status_code == 200
    assert "vérifié" in resp.json()["message"]


@pytest.mark.asyncio
async def test_otp_verify_wrong_code(client: AsyncClient):
    await _redis_mod.redis_client.set(f"otp:{TEST_PHONE}", "123456:0", ex=300)
    resp = await client.post("/api/v1/auth/otp/verify", json={
        "telephone": TEST_PHONE,
        "code": "000000",
    })
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_OTP"


@pytest.mark.asyncio
async def test_otp_verify_expired(client: AsyncClient):
    resp = await client.post("/api/v1/auth/otp/verify", json={
        "telephone": TEST_PHONE,
        "code": "123456",
    })
    assert resp.status_code == 400


# ── Refresh ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient, auth_tokens: dict):
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": auth_tokens["refresh_token"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["access_token"] != auth_tokens["access_token"]


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "token.invalide.bidon",
    })
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "TOKEN_INVALID"


@pytest.mark.asyncio
async def test_refresh_with_access_token_rejected(client: AsyncClient, auth_tokens: dict):
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": auth_tokens["access_token"],
    })
    assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.post("/api/v1/auth/logout", headers=headers)
    assert resp.status_code == 200

    # Le token est blacklisté — toute requête suivante doit échouer
    resp2 = await client.post("/api/v1/auth/logout", headers=headers)
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 401


# ── Password ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_password_change_success(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.post("/api/v1/auth/password/change", headers=headers, json={
        "current_password": "motdepasse123",
        "new_password": "nouveaumdp456",
    })
    assert resp.status_code == 200

    # Ancien mot de passe ne fonctionne plus
    resp2 = await client.post("/api/v1/auth/login", json={
        "telephone": TEST_PHONE,
        "password": "motdepasse123",
    })
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_password_change_wrong_current(client: AsyncClient, auth_tokens: dict):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    resp = await client.post("/api/v1/auth/password/change", headers=headers, json={
        "current_password": "mauvais_mdp",
        "new_password": "nouveaumdp456",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_password_forgot_known_phone(client: AsyncClient, registered_user: dict):
    resp = await client.post("/api/v1/auth/password/forgot", json={"telephone": TEST_PHONE})
    assert resp.status_code == 200
    assert "envoyé" in resp.json()["message"]


@pytest.mark.asyncio
async def test_password_forgot_unknown_phone(client: AsyncClient):
    resp = await client.post("/api/v1/auth/password/forgot", json={"telephone": "+2290100000099"})
    assert resp.status_code == 200  # réponse identique pour éviter l'énumération


@pytest.mark.asyncio
async def test_password_reset_success(client: AsyncClient, registered_user: dict):
    await _redis_mod.redis_client.set(f"otp:{TEST_PHONE}", "654321:0", ex=300)
    resp = await client.post("/api/v1/auth/password/reset", json={
        "telephone": TEST_PHONE,
        "code": "654321",
        "new_password": "resetmdp789",
    })
    assert resp.status_code == 200

    resp2 = await client.post("/api/v1/auth/login", json={
        "telephone": TEST_PHONE,
        "password": "resetmdp789",
    })
    assert resp2.status_code == 200