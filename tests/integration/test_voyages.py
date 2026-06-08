from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ch_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}

def _cl_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ── POST /voyages ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_voyage(client: AsyncClient, voyage: dict):
    assert voyage["ville_depart"] == "Cotonou"
    assert voyage["ville_arrivee"] == "Parakou"
    assert voyage["statut"] == "PUBLIE"
    assert voyage["nombre_places_restantes"] == 4


@pytest.mark.asyncio
async def test_create_voyage_requires_online(
    client: AsyncClient, chauffeur_auth_tokens: dict
):
    headers = _ch_headers(chauffeur_auth_tokens)
    # Ajouter un véhicule sans passer en ligne
    veh_resp = await client.post("/api/v1/chauffeurs/me/vehicules", headers=headers, json={
        "marque": "Honda", "modele": "Civic", "annee": 2021,
        "immatriculation": "BJ-OFFLINE", "couleur": "Noir",
        "type_vehicule": "BERLINE", "nombre_places": 4, "climatise": False,
    })
    vehicule_id = veh_resp.json()["id"]
    date_depart = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    resp = await client.post("/api/v1/voyages", headers=headers, json={
        "ville_depart": "Cotonou", "ville_arrivee": "Abomey",
        "point_depart": "Gare A", "point_arrivee": "Gare B",
        "lat_depart": 6.37, "lng_depart": 2.39,
        "lat_arrivee": 7.18, "lng_arrivee": 1.99,
        "date_depart": date_depart,
        "prix_par_place": 3000, "nombre_places_total": 3,
        "vehicule_id": vehicule_id,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_voyage_wrong_vehicule(
    client: AsyncClient, chauffeur_auth_tokens: dict
):
    headers = _ch_headers(chauffeur_auth_tokens)
    await client.post("/api/v1/chauffeurs/me/online", headers=headers)
    date_depart = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    resp = await client.post("/api/v1/voyages", headers=headers, json={
        "ville_depart": "Cotonou", "ville_arrivee": "Abomey",
        "point_depart": "A", "point_arrivee": "B",
        "lat_depart": 6.37, "lng_depart": 2.39,
        "lat_arrivee": 7.18, "lng_arrivee": 1.99,
        "date_depart": date_depart,
        "prix_par_place": 3000, "nombre_places_total": 3,
        "vehicule_id": "00000000-0000-0000-0000-000000000000",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_voyage_requires_chauffeur_role(
    client: AsyncClient, auth_tokens: dict
):
    headers = _cl_headers(auth_tokens)
    date_depart = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    resp = await client.post("/api/v1/voyages", headers=headers, json={
        "ville_depart": "A", "ville_arrivee": "B",
        "point_depart": "A", "point_arrivee": "B",
        "lat_depart": 0, "lng_depart": 0, "lat_arrivee": 0, "lng_arrivee": 0,
        "date_depart": date_depart,
        "prix_par_place": 3000, "nombre_places_total": 3,
        "vehicule_id": "00000000-0000-0000-0000-000000000000",
    })
    assert resp.status_code == 403


# ── GET /voyages/{id} ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_voyage(client: AsyncClient, auth_tokens: dict, voyage: dict):
    headers = _cl_headers(auth_tokens)
    resp = await client.get(f"/api/v1/voyages/{voyage['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == voyage["id"]


@pytest.mark.asyncio
async def test_get_voyage_unknown(client: AsyncClient, auth_tokens: dict):
    headers = _cl_headers(auth_tokens)
    resp = await client.get(
        "/api/v1/voyages/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert resp.status_code == 404


# ── GET /voyages/me ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_my_voyages(client: AsyncClient, chauffeur_auth_tokens: dict, voyage: dict):
    headers = _ch_headers(chauffeur_auth_tokens)
    resp = await client.get("/api/v1/voyages/me", headers=headers)
    assert resp.status_code == 200
    ids = [v["id"] for v in resp.json()]
    assert voyage["id"] in ids


# ── GET /voyages/search ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_voyages(client: AsyncClient, auth_tokens: dict, voyage: dict):
    headers = _cl_headers(auth_tokens)
    depart_date = datetime.fromisoformat(voyage["date_depart"]).strftime("%Y-%m-%d")
    resp = await client.get("/api/v1/voyages/search", headers=headers, params={
        "ville_depart": "Cotonou",
        "ville_arrivee": "Parakou",
        "date_depart": depart_date,
        "nombre_places": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1
    assert any(v["id"] == voyage["id"] for v in data["items"])


@pytest.mark.asyncio
async def test_search_voyages_no_results(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers = _cl_headers(auth_tokens)
    resp = await client.get("/api/v1/voyages/search", headers=headers, params={
        "ville_depart": "Paris",
        "ville_arrivee": "Lyon",
        "date_depart": "2099-01-01",
        "nombre_places": 1,
    })
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_with_filters(client: AsyncClient, auth_tokens: dict, voyage: dict):
    headers = _cl_headers(auth_tokens)
    depart_date = datetime.fromisoformat(voyage["date_depart"]).strftime("%Y-%m-%d")

    # Filtre climatisé = True → doit trouver le voyage (climatise=True dans fixture)
    resp = await client.get("/api/v1/voyages/search", headers=headers, params={
        "ville_depart": "Cotonou",
        "ville_arrivee": "Parakou",
        "date_depart": depart_date,
        "nombre_places": 1,
        "climatise": True,
    })
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    # Filtre prix_max trop bas → 0 résultats
    resp2 = await client.get("/api/v1/voyages/search", headers=headers, params={
        "ville_depart": "Cotonou",
        "ville_arrivee": "Parakou",
        "date_depart": depart_date,
        "nombre_places": 1,
        "prix_max": 100,
    })
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 0


# ── GET /voyages/popular ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_popular_voyages_public(client: AsyncClient, voyage: dict):
    resp = await client.get("/api/v1/voyages/popular")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── PATCH /voyages/{id} ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_voyage(client: AsyncClient, chauffeur_auth_tokens: dict, voyage: dict):
    headers = _ch_headers(chauffeur_auth_tokens)
    resp = await client.patch(f"/api/v1/voyages/{voyage['id']}", headers=headers, json={
        "prix_par_place": 6000,
    })
    assert resp.status_code == 200
    assert resp.json()["prix_par_place"] == 6000


@pytest.mark.asyncio
async def test_update_voyage_wrong_owner(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    # Un client ne peut pas modifier un voyage
    headers = _cl_headers(auth_tokens)
    resp = await client.patch(f"/api/v1/voyages/{voyage['id']}", headers=headers, json={
        "prix_par_place": 6000,
    })
    assert resp.status_code == 403


# ── POST /voyages/{id}/start, end, cancel ─────────────────────────────────────

@pytest.mark.asyncio
async def test_voyage_lifecycle(client: AsyncClient, chauffeur_auth_tokens: dict, voyage: dict):
    headers = _ch_headers(chauffeur_auth_tokens)
    voyage_id = voyage["id"]

    # start
    resp = await client.post(f"/api/v1/voyages/{voyage_id}/start", headers=headers)
    assert resp.status_code == 200
    status = (await client.get(f"/api/v1/voyages/{voyage_id}", headers=headers)).json()["statut"]
    assert status == "EN_COURS"

    # end
    resp = await client.post(f"/api/v1/voyages/{voyage_id}/end", headers=headers)
    assert resp.status_code == 200
    status = (await client.get(f"/api/v1/voyages/{voyage_id}", headers=headers)).json()["statut"]
    assert status == "TERMINE"

    # ne peut plus être démarré
    resp = await client.post(f"/api/v1/voyages/{voyage_id}/start", headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_cancel_voyage(client: AsyncClient, chauffeur_auth_tokens: dict, voyage: dict):
    headers = _ch_headers(chauffeur_auth_tokens)
    resp = await client.post(f"/api/v1/voyages/{voyage['id']}/cancel", headers=headers)
    assert resp.status_code == 200
    status = (
        await client.get(f"/api/v1/voyages/{voyage['id']}", headers=headers)
    ).json()["statut"]
    assert status == "ANNULE"


@pytest.mark.asyncio
async def test_action_wrong_owner(
    client: AsyncClient, auth_tokens: dict, voyage: dict
):
    headers = _cl_headers(auth_tokens)
    resp = await client.post(f"/api/v1/voyages/{voyage['id']}/start", headers=headers)
    assert resp.status_code == 403


# ── GET /voyages/{id}/passagers ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_passagers_empty(
    client: AsyncClient, chauffeur_auth_tokens: dict, voyage: dict
):
    headers = _ch_headers(chauffeur_auth_tokens)
    resp = await client.get(f"/api/v1/voyages/{voyage['id']}/passagers", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []