# GoTaxi — Guide de migration frontend v1 → v2.1

> **Date :** 2026-05-04
> **API version cible :** 2.1.0
> **Référence complète :** `API_VOYAGES_RESERVATIONS.md`

Ce document liste **uniquement ce qui a changé** par rapport à l'intégration précédente. Chaque section indique ce qui était faux, ce qui est correct maintenant, et le correctif à appliquer.

---

## Sommaire des changements

| # | Priorité | Zone | Résumé |
|---|----------|------|--------|
| 1 | 🔴 BLOQUANT | `ReservationRead` | Nouveau champ `voyage` et `client` dans la réponse |
| 2 | 🔴 BLOQUANT | Colis — recherche | Ne plus utiliser `/voyages/search` pour trouver un voyage pour colis |
| 3 | 🟠 IMPORTANT | accept / reject / cancel | Ces endpoints retournent maintenant `ReservationRead`, plus `MessageResponse` |
| 4 | 🟠 IMPORTANT | Vue chauffeur | Nouvel endpoint `/voyages/{id}/reservations` à utiliser |
| 5 | 🟡 MINEUR | Visibilité voyage EN_COURS | Le client peut voir un voyage EN_COURS s'il a une réservation |

---

## 1. 🔴 `ReservationRead` — champs `voyage` et `client` ajoutés

### Avant (v1)

```json
{
  "id": "uuid",
  "voyage_id": "uuid",
  "client_id": "uuid",
  "nombre_places": 2,
  "prix_total": 7000,
  "statut": "EN_ATTENTE",
  "code_confirmation": "A3F9C1",
  "created_at": "2026-05-04T09:00:00Z"
}
```

Le front devait faire un second appel `GET /voyages/{voyage_id}` ou `GET /users/{client_id}` pour afficher les détails.

### Maintenant (v2.1)

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

Les deux champs peuvent être `null` selon le contexte :

| Endpoint | `voyage` | `client` |
|----------|:--------:|:--------:|
| `GET /reservations/me` | ✅ renseigné | `null` |
| `GET /reservations/me/incoming` (chauffeur) | ✅ renseigné | ✅ renseigné |
| `GET /reservations/{id}` | ✅ renseigné | ✅ renseigné |
| `POST /reservations` (création) | ✅ renseigné | `null` |
| `POST /reservations/{id}/accept` | `null` | ✅ renseigné |
| `POST /reservations/{id}/reject` | `null` | ✅ renseigné |
| `POST /reservations/{id}/cancel` | ✅ renseigné | optionnel |

### Correctifs à appliquer

- **Supprimer** tous les appels secondaires `GET /voyages/{id}` faits juste après une lecture de réservation pour récupérer les infos du trajet — la donnée est maintenant inline.
- **Supprimer** tous les appels secondaires `GET /users/{id}` faits pour afficher le profil client dans la vue chauffeur.
- **Mettre à jour** le modèle/type `Reservation` côté front pour inclure les champs `voyage?: Voyage | null` et `client?: UserPublic | null`.
- **Afficher directement** `reservation.voyage.ville_depart`, `reservation.client.nom`, etc. sans fetch supplémentaire.

---

## 2. 🔴 Envoi de colis — changer l'endpoint de recherche

### Avant (v1 — INCORRECT)

```
// Mauvais : ne retourne que les voyages PUBLIE
GET /api/v1/voyages/search?ville_depart=Cotonou&ville_arrivee=Parakou&date_depart=2026-05-10
```

Résultat : si le voyage est `COMPLET` ou `EN_COURS`, il n'apparaît pas → l'utilisateur voit "aucun voyage disponible" même si un chauffeur est en route.

### Maintenant (v2.1 — CORRECT)

```
// Correct : retourne PUBLIE + COMPLET + EN_COURS avec accepte_colis=true
GET /api/v1/voyages/colis-search?ville_depart=Cotonou&ville_arrivee=Parakou&date_depart=2026-05-10
```

### Règle de routage à respecter côté front

| Cas d'usage | Endpoint à appeler |
|-------------|-------------------|
| Chercher un trajet pour voyager (passager) | `GET /voyages/search` |
| Chercher un voyage pour envoyer un colis | `GET /voyages/colis-search` |

Les deux endpoints ont la même structure de réponse paginée `{ items, total, page, size, pages }`.

`/colis-search` n'expose **pas** le paramètre `nombre_places` (inutile pour un colis) et n'a **pas** les filtres `climatise` / `prix_max` de la recherche passager.

### Paramètres de `/voyages/colis-search`

| Paramètre | Requis | Exemple |
|-----------|:------:|---------|
| `ville_depart` | ✅ | `Cotonou` |
| `ville_arrivee` | ✅ | `Parakou` |
| `date_depart` | ✅ | `2026-05-10` |
| `sort_by` | — | `depart_asc` (défaut) |
| `page` | — | `1` |
| `size` | — | `20` |

### Correctifs à appliquer

- Dans l'écran "Envoyer un colis", remplacer l'appel `/voyages/search` par `/voyages/colis-search`.
- Retirer les filtres `nombre_places`, `climatise`, `prix_max` si ils sont passés dans cette version de la recherche.

---

## 3. 🟠 accept / reject / cancel — type de retour changé

### Avant (v1)

```json
// POST /reservations/{id}/accept  →  200
{ "message": "Réservation confirmée" }

// POST /reservations/{id}/reject  →  200
{ "message": "Réservation refusée" }

// POST /reservations/{id}/cancel  →  200
{ "message": "Réservation annulée" }
```

### Maintenant (v2.1)

Ces trois endpoints retournent désormais `ReservationRead` complet (avec `client` embedded pour le chauffeur).

```json
// POST /reservations/{id}/accept  →  200
{
  "id": "uuid",
  "statut": "CONFIRMEE",
  "client": {
    "nom": "Dossou",
    "prenom": "Marie",
    "photo_url": "https://..."
  },
  "voyage": null,
  ...
}
```

### Correctifs à appliquer

- Mettre à jour les handlers de réponse : au lieu de lire `response.message`, lire `response.statut` et `response.client`.
- Sur l'écran chauffeur "demandes entrantes", après un accept/reject, mettre à jour l'élément de liste directement depuis la réponse (pas besoin de re-fetch la liste).
- Si le front affichait un toast basé sur `response.message`, le remplacer par un message statique ou basé sur `response.statut`.

---

## 4. 🟠 Vue chauffeur — utiliser le nouvel endpoint de réservations

### Avant (v1 — inexistant)

Il n'existait pas d'endpoint pour voir toutes les réservations d'un voyage donné. Le chauffeur ne pouvait voir que les demandes globales via `GET /reservations/me/incoming`.

### Maintenant (v2.1 — disponible)

```
GET /api/v1/voyages/{voyage_id}/reservations
GET /api/v1/voyages/{voyage_id}/reservations?statut=EN_ATTENTE
GET /api/v1/voyages/{voyage_id}/reservations?statut=CONFIRMEE
```

Retourne `list[ReservationRead]` avec `client` embedded.

L'endpoint `GET /reservations/me/incoming` reste disponible mais ne retourne que les `EN_ATTENTE` globaux (tous voyages confondus). Il est utile pour les **notifications**, pas pour la gestion d'un voyage spécifique.

### Recommandation d'usage

| Écran | Endpoint recommandé |
|-------|-------------------|
| Badge / compteur de nouvelles demandes | `GET /reservations/me/incoming` |
| Page détail d'un voyage — onglet "Demandes" | `GET /voyages/{id}/reservations?statut=EN_ATTENTE` |
| Page détail d'un voyage — onglet "Passagers" | `GET /voyages/{id}/passagers` ou `GET /voyages/{id}/reservations?statut=CONFIRMEE` |
| Historique complet d'un voyage | `GET /voyages/{id}/reservations` (sans filtre) |

### Correctifs à appliquer

- Créer (ou corriger) l'écran "Détail voyage chauffeur" pour appeler `GET /voyages/{id}/reservations` au lieu de polling `GET /reservations/me/incoming`.
- Implémenter le filtre par statut pour les onglets Demandes / Passagers.

---

## 5. 🟡 Visibilité d'un voyage EN_COURS pour le client

### Avant (v1)

`GET /voyages/{id}` retournait `404` si le voyage était en statut `EN_COURS` ou `TERMINE`, même si le client avait une réservation dessus.

### Maintenant (v2.1)

Le client **peut** accéder à un voyage `EN_COURS` ou `TERMINE` s'il a une réservation active dessus (`EN_ATTENTE`, `CONFIRMEE` ou `TERMINEE`).

```
// Avant : 404 si voyage EN_COURS
// Maintenant : 200 si le client a une réservation dessus
GET /api/v1/voyages/{voyage_id}
```

### Correctifs à appliquer

- Supprimer toute logique côté front qui bloquait la navigation vers le détail d'un voyage en cours.
- La page de suivi de voyage peut appeler `GET /voyages/{id}` directement pour obtenir le statut à jour.
- Si le front affichait une erreur générique sur 404, gérer maintenant le cas `404` comme "voyage non disponible" (l'utilisateur n'a pas de réservation dessus) sans message trompeur.

---

## Récapitulatif des actions côté front

### Modèles / types à mettre à jour

```typescript
// Avant
interface Reservation {
  id: string
  voyage_id: string
  client_id: string
  nombre_places: number
  prix_total: number
  statut: ReservationStatut
  code_confirmation: string
  created_at: string
}

// Après
interface Reservation {
  id: string
  voyage_id: string
  client_id: string
  nombre_places: number
  prix_total: number
  statut: ReservationStatut
  code_confirmation: string
  created_at: string
  voyage: Voyage | null      // ← NOUVEAU
  client: UserPublic | null  // ← NOUVEAU
}

interface UserPublic {
  id: string
  nom: string
  prenom: string
  photo_url: string | null
  note_moyenne: number
  nombre_avis: number
  role: 'CLIENT' | 'CHAUFFEUR'
}
```

### Appels API à corriger

| Ancien appel | Nouveau comportement |
|-------------|----------------------|
| `GET /voyages/search` pour colis | → `GET /voyages/colis-search` |
| `GET /voyages/{id}` après chaque réservation lue | → Supprimer, `reservation.voyage` est inline |
| `GET /users/{id}` pour profil client (chauffeur) | → Supprimer, `reservation.client` est inline |
| `accept/reject/cancel` → lire `response.message` | → Lire `response.statut` et `response.client` |
| Polling de `GET /reservations/me/incoming` pour les demandes d'un voyage | → `GET /voyages/{id}/reservations?statut=EN_ATTENTE` |

### Appels à ajouter

| Endpoint | Usage |
|----------|-------|
| `GET /voyages/colis-search` | Écran "Envoyer un colis" — recherche de voyages |
| `GET /voyages/{id}/reservations` | Écran "Détail voyage" chauffeur — onglet demandes |
| `GET /voyages/{id}/reservations?statut=CONFIRMEE` | Écran "Détail voyage" chauffeur — onglet passagers |

---

## Aucun changement — ne pas toucher

Ces endpoints n'ont **pas changé** par rapport à la v1 :

- `POST /voyages` — création d'un voyage
- `GET /voyages/me` — liste des voyages du chauffeur
- `GET /voyages/popular` — trajets populaires
- `PATCH /voyages/{id}` — modification d'un voyage
- `POST /voyages/{id}/start` / `/end` / `/cancel`
- `POST /reservations` — création d'une réservation
- `GET /reservations/me` — historique client
- `POST /colis` — création d'un colis *(seul le voyage_id source change, voir §2)*
- `GET /colis/me` — colis du client
- `GET /colis/{id}` — détail colis
- `GET /colis/voyage/{id}` — colis d'un voyage (chauffeur)
- `POST /colis/{id}/confirmer` / `/en_transit` / `/livrer` / `/annuler`