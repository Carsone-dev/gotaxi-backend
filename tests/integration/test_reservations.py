import pytest
from httpx import AsyncClient


def _ch_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}

def _cl_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ── POST /reservations ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_reservation(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers = _cl_headers(auth_tokens)
    resp = await client.post("/api/v1/reservations", headers=headers, json={
        "voyage_id": voyage["id"],
        "nombre_places": 2,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["voyage_id"] == voyage["id"]
    assert data["nombre_places"] == 2
    assert data["prix_total"] == voyage["prix_par_place"] * 2
    assert data["statut"] == "EN_ATTENTE"
    assert len(data["code_confirmation"]) == 6


@pytest.mark.asyncio
async def test_create_reservation_reduces_places(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers_cl = _cl_headers(auth_tokens)
    await client.post("/api/v1/reservations", headers=headers_cl, json={
        "voyage_id": voyage["id"],
        "nombre_places": 2,
    })
    # Vérifier que les places restantes ont diminué
    voyage_resp = await client.get(
        f"/api/v1/voyages/{voyage['id']}", headers=headers_cl
    )
    assert voyage_resp.json()["nombre_places_restantes"] == 2


@pytest.mark.asyncio
async def test_create_reservation_voyage_full(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers = _cl_headers(auth_tokens)
    # Réserver toutes les places
    await client.post("/api/v1/reservations", headers=headers, json={
        "voyage_id": voyage["id"],
        "nombre_places": 4,
    })
    # Vérifier statut COMPLET
    voyage_resp = await client.get(f"/api/v1/voyages/{voyage['id']}", headers=headers)
    assert voyage_resp.json()["statut"] == "COMPLET"

    # Impossible de réserver encore
    resp = await client.post("/api/v1/reservations", headers=headers, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_chauffeur_cannot_reserve_own_voyage(
    client: AsyncClient, chauffeur_auth_tokens: dict, voyage: dict
):
    headers = _ch_headers(chauffeur_auth_tokens)
    resp = await client.post("/api/v1/reservations", headers=headers, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_reservation_insufficient_places(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers = _cl_headers(auth_tokens)
    resp = await client.post("/api/v1/reservations", headers=headers, json={
        "voyage_id": voyage["id"],
        "nombre_places": 5,  # valide par le schéma (≤8), mais voyage n'a que 4 places
    })
    assert resp.status_code == 409


# ── GET /reservations/me ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_my_reservations(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers = _cl_headers(auth_tokens)
    await client.post("/api/v1/reservations", headers=headers, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })
    resp = await client.get("/api/v1/reservations/me", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── GET /reservations/me/incoming ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_incoming_reservations(
    client: AsyncClient, auth_tokens: dict, chauffeur_auth_tokens: dict, voyage: dict
):
    headers_cl = _cl_headers(auth_tokens)
    headers_ch = _ch_headers(chauffeur_auth_tokens)

    # Client crée une réservation
    await client.post("/api/v1/reservations", headers=headers_cl, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })

    # Chauffeur voit la réservation en attente
    resp = await client.get("/api/v1/reservations/me/incoming", headers=headers_ch)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["statut"] == "EN_ATTENTE"


@pytest.mark.asyncio
async def test_incoming_requires_chauffeur_role(
    client: AsyncClient, auth_tokens: dict
):
    headers = _cl_headers(auth_tokens)
    resp = await client.get("/api/v1/reservations/me/incoming", headers=headers)
    assert resp.status_code == 403


# ── GET /reservations/{id} ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_reservation_by_client(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers = _cl_headers(auth_tokens)
    create_resp = await client.post("/api/v1/reservations", headers=headers, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })
    res_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/reservations/{res_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == res_id


@pytest.mark.asyncio
async def test_get_reservation_by_chauffeur(
    client: AsyncClient, auth_tokens: dict, chauffeur_auth_tokens: dict, voyage: dict
):
    headers_cl = _cl_headers(auth_tokens)
    headers_ch = _ch_headers(chauffeur_auth_tokens)

    create_resp = await client.post("/api/v1/reservations", headers=headers_cl, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })
    res_id = create_resp.json()["id"]

    # Le chauffeur (propriétaire du voyage) peut voir la réservation
    resp = await client.get(f"/api/v1/reservations/{res_id}", headers=headers_ch)
    assert resp.status_code == 200


# ── POST /reservations/{id}/accept ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_reservation(
    client: AsyncClient, auth_tokens: dict, chauffeur_auth_tokens: dict, voyage: dict
):
    headers_cl = _cl_headers(auth_tokens)
    headers_ch = _ch_headers(chauffeur_auth_tokens)

    create_resp = await client.post("/api/v1/reservations", headers=headers_cl, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })
    res_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/reservations/{res_id}/accept", headers=headers_ch)
    assert resp.status_code == 200

    # Vérifier le nouveau statut
    res_resp = await client.get(f"/api/v1/reservations/{res_id}", headers=headers_ch)
    assert res_resp.json()["statut"] == "CONFIRMEE"


@pytest.mark.asyncio
async def test_accept_reservation_wrong_chauffeur(
    client: AsyncClient, auth_tokens: dict, chauffeur_auth_tokens: dict, voyage: dict
):
    # Un client ne peut pas accepter une réservation
    headers_cl = _cl_headers(auth_tokens)

    create_resp = await client.post("/api/v1/reservations", headers=headers_cl, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })
    res_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/reservations/{res_id}/accept", headers=headers_cl)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_accept_already_confirmed(
    client: AsyncClient, auth_tokens: dict, chauffeur_auth_tokens: dict, voyage: dict
):
    headers_cl = _cl_headers(auth_tokens)
    headers_ch = _ch_headers(chauffeur_auth_tokens)

    create_resp = await client.post("/api/v1/reservations", headers=headers_cl, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })
    res_id = create_resp.json()["id"]

    await client.post(f"/api/v1/reservations/{res_id}/accept", headers=headers_ch)
    resp = await client.post(f"/api/v1/reservations/{res_id}/accept", headers=headers_ch)
    assert resp.status_code == 400


# ── POST /reservations/{id}/reject ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_reservation_restores_places(
    client: AsyncClient, auth_tokens: dict, chauffeur_auth_tokens: dict, voyage: dict
):
    headers_cl = _cl_headers(auth_tokens)
    headers_ch = _ch_headers(chauffeur_auth_tokens)

    create_resp = await client.post("/api/v1/reservations", headers=headers_cl, json={
        "voyage_id": voyage["id"],
        "nombre_places": 2,
    })
    res_id = create_resp.json()["id"]

    # Places = 2 maintenant
    voyage_before = (
        await client.get(f"/api/v1/voyages/{voyage['id']}", headers=headers_cl)
    ).json()["nombre_places_restantes"]

    resp = await client.post(f"/api/v1/reservations/{res_id}/reject", headers=headers_ch)
    assert resp.status_code == 200

    # Places restaurées
    voyage_after = (
        await client.get(f"/api/v1/voyages/{voyage['id']}", headers=headers_cl)
    ).json()["nombre_places_restantes"]
    assert voyage_after == voyage_before + 2


# ── POST /reservations/{id}/cancel ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_reservation_by_client(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers = _cl_headers(auth_tokens)
    create_resp = await client.post("/api/v1/reservations", headers=headers, json={
        "voyage_id": voyage["id"],
        "nombre_places": 2,
    })
    res_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/reservations/{res_id}/cancel", headers=headers)
    assert resp.status_code == 200

    # Places restaurées
    voyage_resp = await client.get(f"/api/v1/voyages/{voyage['id']}", headers=headers)
    assert voyage_resp.json()["nombre_places_restantes"] == 4


@pytest.mark.asyncio
async def test_cancel_already_cancelled(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers = _cl_headers(auth_tokens)
    create_resp = await client.post("/api/v1/reservations", headers=headers, json={
        "voyage_id": voyage["id"],
        "nombre_places": 1,
    })
    res_id = create_resp.json()["id"]

    await client.post(f"/api/v1/reservations/{res_id}/cancel", headers=headers)
    resp = await client.post(f"/api/v1/reservations/{res_id}/cancel", headers=headers)
    assert resp.status_code == 400


# ── Workflow complet : réservation → accepter → voyage terminé ────────────────

@pytest.mark.asyncio
async def test_full_voyage_workflow(
    client: AsyncClient, auth_tokens: dict, chauffeur_auth_tokens: dict, voyage: dict
):
    headers_cl = _cl_headers(auth_tokens)
    headers_ch = _ch_headers(chauffeur_auth_tokens)
    voyage_id = voyage["id"]

    # Client réserve
    create_resp = await client.post("/api/v1/reservations", headers=headers_cl, json={
        "voyage_id": voyage_id,
        "nombre_places": 1,
    })
    assert create_resp.status_code == 201
    res_id = create_resp.json()["id"]

    # Chauffeur accepte
    await client.post(f"/api/v1/reservations/{res_id}/accept", headers=headers_ch)

    # Chauffeur démarre le voyage
    await client.post(f"/api/v1/voyages/{voyage_id}/start", headers=headers_ch)

    # Chauffeur termine le voyage
    resp = await client.post(f"/api/v1/voyages/{voyage_id}/end", headers=headers_ch)
    assert resp.status_code == 200

    # La réservation CONFIRMEE est passée à TERMINEE
    res_resp = await client.get(f"/api/v1/reservations/{res_id}", headers=headers_ch)
    assert res_resp.json()["statut"] == "TERMINEE"

    # Le voyage est TERMINE
    voyage_resp = await client.get(f"/api/v1/voyages/{voyage_id}", headers=headers_ch)
    assert voyage_resp.json()["statut"] == "TERMINE"