# API GoTaxi — Voyages & Réservations (mise en relation chauffeur ↔ client)

> **Version :** 2.1.0
> **Date :** 2026-05-04
> **Préfixe base :** `/api/v1`
> **Auth :** `Authorization: Bearer <access_token>` sur tous les endpoints sauf mention `Public`

Ce document décrit **l'ensemble des endpoints** liés aux voyages, réservations et colis à implémenter côté mobile. Il couvre les deux perspectives : chauffeur et client.

---

## Sommaire

1. [Schémas de données](#1-schémas-de-données)
2. [Voyages — endpoints chauffeur](#2-voyages--endpoints-chauffeur)
3. [Voyages — endpoints client](#3-voyages--endpoints-client)
4. [Réservations — endpoints chauffeur](#4-réservations--endpoints-chauffeur)
5. [Réservations — endpoints client](#5-réservations--endpoints-client)
6. [Colis sur un voyage](#6-colis-sur-un-voyage)
7. [Flux complets scénarios](#7-flux-complets-scénarios)
8. [Règles métier importantes](#8-règles-métier-importantes)

---

## 1. Schémas de données

### `VoyageRead`

```json
{
  "id": "uuid",
  "chauffeur_id": "uuid",
  "vehicule_id": "uuid",
  "ville_depart": "Cotonou",
  "ville_arrivee": "Parakou",
  "point_depart": "Gare de Godomey",
  "point_arrivee": "Gare de Parakou",
  "date_depart": "2026-05-10T06:00:00Z",
  "date_arrivee_estimee": "2026-05-10T13:00:00Z",
  "prix_par_place": 3500,
  "nombre_places_restantes": 2,
  "nombre_places_total": 4,
  "accepte_colis": true,
  "climatise": true,
  "non_fumeur": true,
  "statut": "PUBLIE",
  "distance_km": null,
  "created_at": "2026-05-04T08:00:00Z"
}
```

**Statuts possibles :** `PUBLIE` · `COMPLET` · `EN_COURS` · `TERMINE` · `ANNULE`

---

### `ReservationRead`

> **Nouveau :** les champs `voyage` et `client` sont désormais **embedded** dans la réponse.

```json
{
  "id": "uuid",
  "voyage_id": "uuid",
  "client_id": "uuid",
  "nombre_places": 2,
  "prix_total": 7000,
  "statut": "EN_ATTENTE",
  "code_confirmation": "A3F9C1",
  "created_at": "2026-05-04T09:00:00Z",

  "voyage": {
    "id": "uuid",
    "ville_depart": "Cotonou",
    "ville_arrivee": "Parakou",
    "date_depart": "2026-05-10T06:00:00Z",
    "prix_par_place": 3500,
    "statut": "PUBLIE"
  },

  "client": {
    "id": "uuid",
    "nom": "Dossou",
    "prenom": "Marie",
    "photo_url": "https://...",
    "note_moyenne": 4.8,
    "nombre_avis": 5,
    "role": "CLIENT"
  }
}
```

**Statuts possibles :** `EN_ATTENTE` · `CONFIRMEE` · `REFUSEE` · `ANNULEE` · `TERMINEE`

> - Le champ `voyage` est renseigné pour la **vue client** (il voit son trajet).
> - Le champ `client` est renseigné pour la **vue chauffeur** (il voit qui veut voyager).
> - Les deux sont présents dans le détail `GET /reservations/{id}`.

---

### `UserPublic` (profil condensé dans `client`)

```json
{
  "id": "uuid",
  "nom": "Dossou",
  "prenom": "Marie",
  "photo_url": "https://...",
  "note_moyenne": 4.8,
  "nombre_avis": 5,
  "role": "CLIENT"
}
```

---

### `ColisRead`

```json
{
  "id": "uuid",
  "voyage_id": "uuid",
  "expediteur_id": "uuid",
  "ville_depart": "Cotonou",
  "ville_arrivee": "Parakou",
  "description": "Vêtements pour ma sœur",
  "categorie": "VETEMENTS",
  "poids_kg": 3.5,
  "fragile": false,
  "destinataire_nom": "Aïcha Mama",
  "destinataire_telephone": "+22967890123",
  "prix": null,
  "statut": "EN_ATTENTE",
  "code_suivi": "GTX-A3B4C5",
  "photo_url": null,
  "voyage": { "...VoyageRead..." },
  "created_at": "2026-05-04T10:00:00Z",
  "updated_at": "2026-05-04T10:00:00Z"
}
```

**Statuts colis :** `EN_ATTENTE` · `CONFIRME` · `EN_TRANSIT` · `LIVRE` · `ANNULE`

**Catégories :** `DOCUMENTS` · `VETEMENTS` · `ELECTRONIQUE` · `ALIMENTAIRE` · `FRAGILE` · `AUTRE`

---

## 2. Voyages — endpoints chauffeur

### `POST /voyages`
Publier un nouveau trajet.

**Auth :** Chauffeur · KYC validé · En ligne · Véhicule actif

**Request body**
```json
{
  "ville_depart": "Cotonou",
  "ville_arrivee": "Parakou",
  "point_depart": "Gare de Godomey",
  "point_arrivee": "Gare de Parakou",
  "lat_depart": 6.3703,
  "lng_depart": 2.3912,
  "lat_arrivee": 9.3379,
  "lng_arrivee": 2.6286,
  "date_depart": "2026-05-10T06:00:00Z",
  "prix_par_place": 3500,
  "nombre_places_total": 4,
  "accepte_colis": true,
  "climatise": true,
  "non_fumeur": true,
  "vehicule_id": "uuid-vehicule"
}
```

**Response 201** → `VoyageRead`

**Erreurs**
| Code | Raison |
|------|--------|
| `403` | KYC non validé ou chauffeur hors ligne |
| `404` | Véhicule introuvable ou inactif |

---

### `GET /voyages/me`
Tous ses voyages publiés (historique complet).

**Response 200** → `list[VoyageRead]` triés par date décroissante

---

### `GET /voyages/{voyage_id}`
Détail d'un de ses voyages.

**Response 200** → `VoyageRead`

**Erreurs**
| Code | Raison |
|------|--------|
| `403` | Ce voyage ne lui appartient pas |
| `404` | Voyage introuvable |

---

### `PATCH /voyages/{voyage_id}`
Modifier un voyage avant le départ (uniquement si statut `PUBLIE`).

**Request body** (tous les champs sont optionnels)
```json
{
  "prix_par_place": 4000,
  "point_depart": "Nouveau point",
  "date_depart": "2026-05-10T07:00:00Z",
  "accepte_colis": false,
  "non_fumeur": true
}
```

**Response 200** → `VoyageRead`

**Erreurs**
| Code | Raison |
|------|--------|
| `400` | Voyage non modifiable (statut ≠ PUBLIE) |

---

### `POST /voyages/{voyage_id}/start`
Démarrer le trajet : `PUBLIE` ou `COMPLET` → `EN_COURS`.

**Response 200** `{ "message": "Voyage démarré" }`

---

### `POST /voyages/{voyage_id}/end`
Terminer le trajet : `EN_COURS` → `TERMINE`.
Toutes les réservations `CONFIRMEE` passent en `TERMINEE`.

**Response 200** `{ "message": "Voyage terminé" }`

---

### `POST /voyages/{voyage_id}/cancel`
Annuler le trajet : `PUBLIE` ou `COMPLET` → `ANNULE`.
Toutes les réservations actives (`EN_ATTENTE`, `CONFIRMEE`) passent en `ANNULEE`.

**Response 200** `{ "message": "Voyage annulé" }`

---

## 3. Voyages — endpoints client

### `GET /voyages/search`
Rechercher des trajets disponibles.

**Auth :** Bearer

**Query params**

| Paramètre | Type | Requis | Défaut | Description |
|-----------|------|:------:|--------|-------------|
| `ville_depart` | string | ✅ | — | Ex: `Cotonou` |
| `ville_arrivee` | string | ✅ | — | Ex: `Parakou` |
| `date_depart` | date | ✅ | — | Format `YYYY-MM-DD` |
| `nombre_places` | int | — | `1` | Nombre de places souhaitées |
| `accepte_colis` | bool | — | — | Filtrer si accepte colis |
| `climatise` | bool | — | — | Filtrer si climatisé |
| `prix_max` | int | — | — | Prix max par place (FCFA) |
| `sort_by` | string | — | `depart_asc` | `prix_asc` · `prix_desc` · `depart_asc` · `depart_desc` |
| `page` | int | — | `1` | Numéro de page |
| `size` | int | — | `20` | Max `100` |

**Response 200**
```json
{
  "items": [ "...list[VoyageRead]..." ],
  "total": 12,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

> Seuls les voyages avec statut `PUBLIE` apparaissent dans la recherche.

---

### `GET /voyages/popular`
Trajets populaires pour la page d'accueil.

**Auth :** Public (aucun token requis)

**Response 200** → `list[VoyageRead]` (10 premiers PUBLIE, triés par date)

---

### `GET /voyages/colis-search` ⭐ Nouveau
Rechercher des voyages disponibles pour **envoyer un colis**.

**Auth :** Bearer

> Contrairement à `/voyages/search` (passagers), cet endpoint retourne aussi les voyages `COMPLET` et `EN_COURS` — un chauffeur peut accepter des colis même après le départ ou quand le véhicule est plein de passagers. Pas de filtre sur les places restantes.

**Query params**

| Paramètre | Type | Requis | Défaut | Description |
|-----------|------|:------:|--------|-------------|
| `ville_depart` | string | ✅ | — | Ex: `Cotonou` |
| `ville_arrivee` | string | ✅ | — | Ex: `Parakou` |
| `date_depart` | date | ✅ | — | Format `YYYY-MM-DD` |
| `sort_by` | string | — | `depart_asc` | `prix_asc` · `prix_desc` · `depart_asc` · `depart_desc` |
| `page` | int | — | `1` | Numéro de page |
| `size` | int | — | `20` | Max `100` |

**Statuts retournés :** `PUBLIE` · `COMPLET` · `EN_COURS`
*(seuls les voyages avec `accepte_colis = true` apparaissent)*

**Response 200**
```json
{
  "items": [ "...list[VoyageRead]..." ],
  "total": 5,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

**Erreurs**
| Code | Raison |
|------|--------|
| `422` | Paramètre obligatoire manquant (`ville_depart`, `ville_arrivee`, `date_depart`) |

---

### `GET /voyages/{voyage_id}`
Détail d'un voyage.

**Auth :** Bearer

**Règles de visibilité client :**
- Voyage `PUBLIE` ou `COMPLET` → toujours accessible
- Voyage `EN_COURS` ou `TERMINE` → accessible **uniquement** si le client a une réservation active (`EN_ATTENTE`, `CONFIRMEE` ou `TERMINEE`) sur ce voyage

**Response 200** → `VoyageRead`

**Erreurs**
| Code | Raison |
|------|--------|
| `404` | Voyage inexistant ou non visible pour ce client |

---

## 4. Réservations — endpoints chauffeur

### `GET /voyages/{voyage_id}/reservations` ⭐ Nouveau
Vue complète de toutes les réservations sur un voyage.

**Auth :** Chauffeur (propriétaire du voyage)

**Query params**

| Paramètre | Type | Requis | Description |
|-----------|------|:------:|-------------|
| `statut` | enum | — | Filtrer : `EN_ATTENTE` · `CONFIRMEE` · `REFUSEE` · `ANNULEE` · `TERMINEE` |

**Exemple d'appel**
```
GET /api/v1/voyages/{id}/reservations
GET /api/v1/voyages/{id}/reservations?statut=EN_ATTENTE
GET /api/v1/voyages/{id}/reservations?statut=CONFIRMEE
```

**Response 200** → `list[ReservationRead]`
Chaque réservation contient le **profil client** (`client.nom`, `client.photo_url`, `client.note_moyenne`).

```json
[
  {
    "id": "uuid",
    "voyage_id": "uuid",
    "client_id": "uuid",
    "nombre_places": 2,
    "prix_total": 7000,
    "statut": "EN_ATTENTE",
    "code_confirmation": "A3F9C1",
    "created_at": "2026-05-04T09:00:00Z",
    "voyage": null,
    "client": {
      "id": "uuid",
      "nom": "Dossou",
      "prenom": "Marie",
      "photo_url": "https://...",
      "note_moyenne": 4.8,
      "nombre_avis": 5,
      "role": "CLIENT"
    }
  }
]
```

---

### `GET /voyages/{voyage_id}/passagers`
Passagers confirmés uniquement (statut `CONFIRMEE`).

**Auth :** Chauffeur (propriétaire du voyage)

**Response 200** → `list[ReservationRead]` avec `client` embedded

> Utiliser cet endpoint pour afficher la liste des passagers embarqués une fois le voyage démarré.

---

### `GET /reservations/me/incoming`
Toutes les demandes EN_ATTENTE sur ses voyages.

**Auth :** Chauffeur

**Response 200** → `list[ReservationRead]` avec `voyage` + `client` embedded

> Endpoint principal pour la **notification de nouvelles demandes**. Poller régulièrement ou écouter via WebSocket `/ws/notifications`.

---

### `GET /reservations/{reservation_id}`
Détail d'une réservation.

**Auth :** Bearer (chauffeur du voyage ou client propriétaire)

**Response 200** → `ReservationRead` complet (`voyage` + `client` embedded)

---

### `POST /reservations/{reservation_id}/accept`
Accepter une demande : `EN_ATTENTE` → `CONFIRMEE`.

**Auth :** Chauffeur

**Response 200** → `ReservationRead` (avec profil client)

**Erreurs**
| Code | Raison |
|------|--------|
| `400` | Réservation pas en statut EN_ATTENTE |
| `403` | Réservation hors de son voyage |
| `404` | Réservation introuvable |

---

### `POST /reservations/{reservation_id}/reject`
Refuser une demande : `EN_ATTENTE` → `REFUSEE`.
Les places sont restituées au voyage.

**Auth :** Chauffeur

**Response 200** → `ReservationRead`

---

### `POST /reservations/{reservation_id}/cancel`
Annuler une réservation confirmée (chauffeur ou client).
Les places sont restituées si le voyage est encore actif.

**Auth :** Bearer (chauffeur ou client concerné)

**Response 200** → `ReservationRead`

---

## 5. Réservations — endpoints client

### `POST /reservations`
Créer une réservation sur un voyage.

**Auth :** Bearer

**Request body**
```json
{
  "voyage_id": "uuid-du-voyage",
  "nombre_places": 2
}
```

**Response 201** → `ReservationRead` avec `voyage` embedded

```json
{
  "id": "uuid",
  "nombre_places": 2,
  "prix_total": 7000,
  "statut": "EN_ATTENTE",
  "code_confirmation": "A3F9C1",
  "created_at": "...",
  "voyage": {
    "ville_depart": "Cotonou",
    "ville_arrivee": "Parakou",
    "date_depart": "2026-05-10T06:00:00Z",
    "prix_par_place": 3500,
    "statut": "PUBLIE"
  },
  "client": null
}
```

**Règles**
- Le voyage doit être en statut `PUBLIE`
- Les places demandées doivent être disponibles (`nombre_places_restantes >= nombre_places`)
- Un chauffeur ne peut pas réserver sur son propre voyage

**Erreurs**
| Code | Raison |
|------|--------|
| `403` | Chauffeur essaie de réserver son propre voyage |
| `404` | Voyage introuvable |
| `409` | Plus de places ou voyage non PUBLIE |

---

### `GET /reservations/me`
Historique complet de ses réservations avec détails voyage.

**Auth :** Bearer

**Response 200** → `list[ReservationRead]` triées par date décroissante, `voyage` embedded

```json
[
  {
    "id": "uuid",
    "statut": "CONFIRMEE",
    "nombre_places": 2,
    "prix_total": 7000,
    "code_confirmation": "A3F9C1",
    "voyage": {
      "ville_depart": "Cotonou",
      "ville_arrivee": "Parakou",
      "date_depart": "2026-05-10T06:00:00Z",
      "statut": "EN_COURS"
    },
    "client": null
  }
]
```

---

### `GET /reservations/{reservation_id}`
Détail d'une réservation spécifique.

**Auth :** Bearer (le client propriétaire)

**Response 200** → `ReservationRead` avec `voyage` embedded

---

### `POST /reservations/{reservation_id}/cancel`
Annuler sa propre réservation.

**Auth :** Bearer

**Conditions**
- Statut doit être `EN_ATTENTE` ou `CONFIRMEE`
- Le voyage doit ne pas être encore `TERMINE` ou `ANNULE`

**Response 200** → `ReservationRead` avec `statut: "ANNULEE"`

---

## 6. Colis sur un voyage

### `POST /colis`
Envoyer un colis sur un voyage existant.

**Auth :** Bearer (client)

**Request body**
```json
{
  "voyage_id": "uuid-du-voyage",
  "description": "Vêtements pour ma sœur",
  "categorie": "VETEMENTS",
  "poids_kg": 3.5,
  "fragile": false,
  "destinataire_nom": "Aïcha Mama",
  "destinataire_telephone": "+22967890123"
}
```

**Response 201** → `ColisRead` avec `code_suivi` généré (`GTX-XXXXXX`)

---

### `GET /colis/me`
Mes colis envoyés.

**Auth :** Bearer (client)

**Response 200** → `list[ColisRead]`

---

### `GET /colis/voyage/{voyage_id}` ⭐ Vue chauffeur
Tous les colis rattachés à un voyage du chauffeur.

**Auth :** Chauffeur (propriétaire du voyage)

**Response 200** → `list[ColisRead]`

> Endpoint principal pour que le chauffeur voie **quels colis il doit transporter** sur chaque voyage.

---

### `GET /colis/{colis_id}`
Détail d'un colis.

**Auth :** Bearer (expéditeur ou chauffeur du voyage)

**Response 200** → `ColisRead`

---

### Workflow colis — actions chauffeur

| Endpoint | Transition | Description |
|----------|-----------|-------------|
| `POST /colis/{id}/confirmer` | `EN_ATTENTE` → `CONFIRME` | Chauffeur accepte le colis |
| `POST /colis/{id}/en_transit` | `CONFIRME` → `EN_TRANSIT` | Colis pris en charge, voyage `EN_COURS` requis |
| `POST /colis/{id}/livrer` | `EN_TRANSIT` → `LIVRE` | Colis livré au destinataire |
| `POST /colis/{id}/annuler` | `EN_ATTENTE` → `ANNULE` | Chauffeur ou client annule |

**Erreurs communes**
| Code | Raison |
|------|--------|
| `409` | Statut actuel incompatible avec l'action |
| `403` | Pas le chauffeur du voyage |
| `422` | `en_transit` : voyage pas encore `EN_COURS` |

---

## 7. Flux complets scénarios

### Scénario A — Client réserve un voyage

```
CLIENT                                    CHAUFFEUR
  │                                           │
  ├─ GET /voyages/search ──────────────────▶  │
  │   └── Voir voyages PUBLIE                 │
  │                                           │
  ├─ POST /reservations ───────────────────▶  │
  │   └── Réservation EN_ATTENTE créée        │
  │   └── Voyage embedded dans la réponse     │
  │                                           │
  │         ◀── Notification push ────────────┤
  │         GET /reservations/me/incoming     │
  │         └── Voir demande + profil client  │
  │                                           │
  │         POST /reservations/{id}/accept ──▶│
  │         └── Réservation → CONFIRMEE       │
  │                                           │
  │ ◀── Notification push ────────────────────┤
  ├─ GET /reservations/{id} ───────────────▶  │
  │   └── Voir statut CONFIRMEE               │
  │   └── Voir infos voyage embedded          │
  │                                           │
  │         POST /voyages/{id}/start ────────▶│
  │         └── Voyage → EN_COURS             │
  │                                           │
  ├─ GET /voyages/{id} ────────────────────▶  │
  │   └── Accessible car réservation active   │
  │   └── Voir statut EN_COURS                │
  │                                           │
  │         POST /voyages/{id}/end ──────────▶│
  │         └── Voyage → TERMINE              │
  │         └── Réservations → TERMINEE       │
```

---

### Scénario B — Chauffeur gère son voyage complet

```
1.  POST /voyages
    └── Publier le trajet (KYC validé + en ligne requis)

2.  GET /voyages/{id}/reservations
    └── Voir toutes les demandes entrantes avec profil client

3.  GET /voyages/{id}/reservations?statut=EN_ATTENTE
    └── Filtrer uniquement les demandes à traiter

4.  POST /reservations/{id}/accept   (ou /reject)
    └── Répondre à chaque demande

5.  GET /voyages/{id}/passagers
    └── Liste finale des passagers confirmés

6.  GET /colis/voyage/{id}
    └── Liste des colis à transporter

7.  POST /voyages/{id}/start
    └── Démarrer le trajet

8.  POST /colis/{id}/en_transit  (pour chaque colis)
    └── Marquer les colis en route

9.  POST /colis/{id}/livrer  (à destination)
    └── Confirmer la livraison de chaque colis

10. POST /voyages/{id}/end
    └── Clôturer le voyage
```

---

### Scénario C — Client suit son voyage en temps réel

```
1.  GET /reservations/me
    └── Trouver sa réservation, récupérer voyage_id

2.  GET /voyages/{voyage_id}
    └── Voir statut EN_COURS (accès car réservation active)

3.  WS  ws://host/ws/tracking/voyage/{voyage_id}
    └── Recevoir position GPS chauffeur en temps réel

    Message reçu :
    {
      "type": "position_update",
      "voyage_id": "...",
      "lat": 7.1234,
      "lng": 2.4321,
      "vitesse": 85.0,
      "heading": 30.0,
      "timestamp": "2026-05-10T09:15:00Z"
    }
```

---

### Scénario D — Client envoie un colis sur un voyage en cours

```
CLIENT                                    CHAUFFEUR
  │                                           │
  ├─ GET /voyages/colis-search ─────────────▶ │
  │   └── Paramètres: ville_depart, ville_arrivee, date_depart
  │   └── Retourne PUBLIE + COMPLET + EN_COURS avec accepte_colis=true
  │                                           │
  ├─ POST /colis ──────────────────────────▶  │
  │   └── voyage_id, description, categorie   │
  │   └── Colis EN_ATTENTE créé              │
  │   └── code_suivi: "GTX-A3B4C5"           │
  │                                           │
  │         ◀── Notification push ────────────┤
  │         GET /colis/voyage/{id}            │
  │         └── Voir le nouveau colis         │
  │                                           │
  │         POST /colis/{id}/confirmer ──────▶│
  │         └── Colis → CONFIRME             │
  │                                           │
  │ ◀── Notification push ────────────────────┤
  ├─ GET /colis/{id} ───────────────────────▶ │
  │   └── Voir statut CONFIRME               │
  │                                           │
  │         POST /colis/{id}/en_transit ─────▶│
  │         └── Colis → EN_TRANSIT           │
  │         └── (voyage doit être EN_COURS)   │
  │                                           │
  ├─ GET /colis/{id} ───────────────────────▶ │
  │   └── Voir statut EN_TRANSIT             │
  │                                           │
  │         POST /colis/{id}/livrer ─────────▶│
  │         └── Colis → LIVRE                │
  │                                           │
  ├─ GET /colis/me ─────────────────────────▶ │
  │   └── Historique avec statut LIVRE        │
```

> **Cas d'usage typique :** un chauffeur est déjà en route (voyage `EN_COURS`) ou a son véhicule complet de passagers (voyage `COMPLET`). Le client recherche via `/colis-search` et trouve ce voyage — l'envoi reste possible car le colis ne prend pas de place passager.

---

## 8. Règles métier importantes

### Réservations

| Règle | Détail |
|-------|--------|
| **Visibilité symétrique** | Le chauffeur voit le profil du client dans toutes ses réservations. Le client voit les infos du voyage dans toutes ses réservations. |
| **Places restituées** | Sur `reject` ou `cancel`, `nombre_places_restantes` est restauré sur le voyage. Si le voyage était `COMPLET`, il repasse en `PUBLIE`. |
| **Pas d'auto-réservation** | Un chauffeur ne peut pas créer de réservation sur son propre voyage (403). |
| **Statuts terminaux** | `REFUSEE`, `ANNULEE`, `TERMINEE` sont irréversibles via l'API. |

### Voyages

| Règle | Détail |
|-------|--------|
| **COMPLET** | Quand `nombre_places_restantes = 0`, le voyage passe automatiquement en `COMPLET`. Il n'apparaît plus dans `/search` mais reste visible pour les clients avec réservation. |
| **EN_COURS visible** | Un voyage `EN_COURS` ou `TERMINE` est visible par le client **uniquement** s'il a une réservation en statut `EN_ATTENTE`, `CONFIRMEE` ou `TERMINEE`. |
| **Modification** | Un voyage n'est modifiable (`PATCH`) que si son statut est `PUBLIE`. |

### Colis

| Règle | Détail |
|-------|--------|
| **Voyage requis** | Un colis est toujours rattaché à un voyage (`voyage_id` obligatoire). |
| **Statuts acceptés pour colis** | `POST /colis` n'accepte que les voyages en statut `PUBLIE`, `COMPLET` ou `EN_COURS`. Un voyage `TERMINE` ou `ANNULE` retourne `422`. |
| **Recherche dédiée** | Utiliser `GET /voyages/colis-search` et non `/voyages/search` pour trouver un voyage destiné à recevoir un colis. |
| **`en_transit` bloqué** | Le passage `CONFIRME → EN_TRANSIT` est refusé si le voyage n'est pas `EN_COURS`. |
| **Vue chauffeur** | `GET /colis/voyage/{voyage_id}` liste tous les colis d'un voyage (tous statuts). |

---

## Résumé des endpoints pour l'intégration mobile

### Chauffeur

| Méthode | Endpoint | Usage |
|---------|----------|-------|
| `POST` | `/voyages` | Publier un trajet |
| `GET` | `/voyages/me` | Mes voyages |
| `GET` | `/voyages/{id}` | Détail d'un voyage |
| `PATCH` | `/voyages/{id}` | Modifier avant départ |
| `POST` | `/voyages/{id}/start` | Démarrer |
| `POST` | `/voyages/{id}/end` | Terminer |
| `POST` | `/voyages/{id}/cancel` | Annuler |
| `GET` | `/voyages/{id}/reservations` | **Toutes les demandes** (avec filtre statut) |
| `GET` | `/voyages/{id}/passagers` | Passagers confirmés |
| `GET` | `/reservations/me/incoming` | Demandes EN_ATTENTE globales |
| `POST` | `/reservations/{id}/accept` | Accepter |
| `POST` | `/reservations/{id}/reject` | Refuser |
| `POST` | `/reservations/{id}/cancel` | Annuler |
| `GET` | `/colis/voyage/{id}` | **Colis du voyage** |
| `POST` | `/colis/{id}/confirmer` | Accepter un colis |
| `POST` | `/colis/{id}/en_transit` | Colis en route |
| `POST` | `/colis/{id}/livrer` | Colis livré |

### Client

| Méthode | Endpoint | Usage |
|---------|----------|-------|
| `GET` | `/voyages/search` | Rechercher un trajet (passagers) |
| `GET` | `/voyages/colis-search` | **Rechercher un voyage pour colis** (PUBLIE+COMPLET+EN_COURS) |
| `GET` | `/voyages/popular` | Trajets populaires (accueil) |
| `GET` | `/voyages/{id}` | Détail (accessible même EN_COURS si réservation) |
| `POST` | `/reservations` | Réserver |
| `GET` | `/reservations/me` | Mes réservations + voyage embedded |
| `GET` | `/reservations/{id}` | Détail réservation |
| `POST` | `/reservations/{id}/cancel` | Annuler |
| `POST` | `/colis` | Envoyer un colis |
| `GET` | `/colis/me` | Mes colis |
| `GET` | `/colis/{id}` | Détail colis |
| `POST` | `/colis/{id}/annuler` | Annuler un colis |
| `WS` | `/ws/tracking/voyage/{id}` | Position GPS en direct |
| `WS` | `/ws/notifications` | Notifications temps réel |