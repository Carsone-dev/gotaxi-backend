# GoTaxi API — Utilisateurs · Chauffeurs · Voyages · Réservations · Prêt à consommer

> **Base URL** : `http://<host>:8001/api/v1`  
> **Documentation interactive** : `http://<host>:8001/docs`  
> **Format** : JSON — `Content-Type: application/json`  
> **Authentification** : Bearer JWT — `Authorization: Bearer <access_token>`  
> **Complète** : [`API_AUTH_READY.md`](./API_AUTH_READY.md) — Auth (register, login, OTP, refresh, logout, password)

---

## Statut des endpoints

| Module | Endpoint | Méthode | Auth requise |
|---|---|---|---|
| **Utilisateurs** | `/users/me` | GET | Bearer |
| | `/users/me` | PATCH | Bearer |
| | `/users/me` | DELETE | Bearer |
| | `/users/me/photo` | POST | Bearer |
| | `/users/me/fcm-token` | POST | Bearer |
| | `/users/me/avis` | GET | Bearer |
| | `/users/{user_id}` | GET | Bearer |
| **Chauffeurs** | `/chauffeurs/me` | GET | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me` | PATCH | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/documents` | POST | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/online` | POST | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/offline` | POST | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/position` | POST | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/stats` | GET | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/revenus` | GET | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/vehicules` | GET | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/vehicules` | POST | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/vehicules/{id}` | PATCH | Bearer (CHAUFFEUR) |
| | `/chauffeurs/me/vehicules/{id}` | DELETE | Bearer (CHAUFFEUR) |
| | `/chauffeurs/{id}` | GET | Bearer |
| | `/chauffeurs/{id}/voyages` | GET | Bearer |
| **Voyages** | `/voyages` | POST | Bearer (CHAUFFEUR) |
| | `/voyages/search` | GET | Bearer |
| | `/voyages/popular` | GET | Public |
| | `/voyages/me` | GET | Bearer (CHAUFFEUR) |
| | `/voyages/{id}` | GET | Bearer |
| | `/voyages/{id}` | PATCH | Bearer (CHAUFFEUR, owner) |
| | `/voyages/{id}/start` | POST | Bearer (CHAUFFEUR, owner) |
| | `/voyages/{id}/end` | POST | Bearer (CHAUFFEUR, owner) |
| | `/voyages/{id}/cancel` | POST | Bearer (CHAUFFEUR, owner) |
| | `/voyages/{id}/passagers` | GET | Bearer (CHAUFFEUR, owner) |
| **Réservations** | `/reservations` | POST | Bearer |
| | `/reservations/me` | GET | Bearer |
| | `/reservations/me/incoming` | GET | Bearer (CHAUFFEUR) |
| | `/reservations/{id}` | GET | Bearer (owner ou chauffeur du voyage) |
| | `/reservations/{id}/accept` | POST | Bearer (CHAUFFEUR, owner voyage) |
| | `/reservations/{id}/reject` | POST | Bearer (CHAUFFEUR, owner voyage) |
| | `/reservations/{id}/cancel` | POST | Bearer (client ou chauffeur) |

---

## UTILISATEURS

### 1. Mon profil

```
GET /users/me
Authorization: Bearer <access_token>
```

**Réponse 200**

```json
{
  "id": "uuid",
  "telephone": "+2290100000001",
  "email": "marc@example.com",
  "nom": "Koffi",
  "prenom": "Marc",
  "photo_url": "https://bucket.s3.region.amazonaws.com/profiles/uuid.jpg",
  "role": "CLIENT",
  "statut": "ACTIF",
  "telephone_verifie": true,
  "note_moyenne": 4.8,
  "nombre_avis": 12,
  "langue": "fr",
  "created_at": "2026-04-01T10:00:00Z"
}
```

| Champ | Type | Description |
|---|---|---|
| `role` | string | `CLIENT` \| `CHAUFFEUR` \| `ADMIN` \| `SUPER_ADMIN` |
| `statut` | string | `ACTIF` \| `SUSPENDU` \| `EN_ATTENTE_KYC` \| `SUPPRIME` |
| `telephone_verifie` | bool | `false` tant que l'OTP n'a pas été vérifié |

---

### 2. Modifier mon profil

```
PATCH /users/me
Authorization: Bearer <access_token>
```

**Corps** — tous les champs sont optionnels

```json
{
  "nom": "Nouveau Nom",
  "prenom": "Nouveau Prénom",
  "email": "nouveau@email.com",
  "langue": "fr"
}
```

**Réponse 200** : profil mis à jour (même structure que `GET /users/me`)

---

### 3. Upload photo de profil

```
POST /users/me/photo
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

| Champ | Type | Contrainte |
|---|---|---|
| `file` | fichier | JPEG, PNG ou WebP — max 5 Mo |

**Réponse 200** : profil avec `photo_url` mis à jour

```json
// 400 — format ou taille invalide
{ "detail": "Type d'image non supporté. Utilisez JPEG, PNG ou WebP." }
```

---

### 4. Enregistrer le token push (FCM)

```
POST /users/me/fcm-token?token=<fcm_token>
Authorization: Bearer <access_token>
```

> Appeler cet endpoint dès que l'application obtient un nouveau token FCM (au lancement ou après rotation).

**Réponse 200**

```json
{ "message": "Token FCM enregistré" }
```

---

### 5. Supprimer mon compte

```
DELETE /users/me
Authorization: Bearer <access_token>
```

Suppression logique (soft delete) — le compte passe en `SUPPRIME`. Toutes les requêtes suivantes avec ce token retournent 401.

**Réponse 200**

```json
{ "message": "Compte supprimé" }
```

---

### 6. Mes avis reçus

```
GET /users/me/avis
Authorization: Bearer <access_token>
```

**Réponse 200**

```json
[
  {
    "id": "uuid",
    "auteur_id": "uuid",
    "cible_id": "uuid",
    "voyage_id": "uuid",
    "note": 5,
    "commentaire": "Très bon conducteur",
    "tags": ["ponctuel", "propre"],
    "signale": false,
    "visible": true,
    "created_at": "2026-04-10T08:00:00Z"
  }
]
```

---

### 7. Profil public d'un utilisateur

```
GET /users/{user_id}
Authorization: Bearer <access_token>
```

**Réponse 200** — champs publics uniquement (pas de téléphone, pas de hash)

```json
{
  "id": "uuid",
  "nom": "Koffi",
  "prenom": "Marc",
  "photo_url": "https://...",
  "role": "CLIENT",
  "note_moyenne": 4.8,
  "nombre_avis": 12
}
```

```json
// 404 — utilisateur introuvable ou supprimé
{ "detail": "Utilisateur introuvable" }
```

---

## CHAUFFEURS

### 8. Mon profil chauffeur

```
GET /chauffeurs/me
Authorization: Bearer <access_token>   (rôle CHAUFFEUR obligatoire)
```

**Réponse 200**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "cin_numero": "BE1234567",
  "permis_numero": "P987654",
  "permis_expiration": "2028-01-01",
  "kyc_valide": true,
  "kyc_valide_le": "2026-04-01",
  "autorisation_transfrontaliere": false,
  "en_ligne": false,
  "derniere_position_lat": 6.3703,
  "derniere_position_lng": 2.3912,
  "nombre_trajets": 142,
  "revenus_total": 710000,
  "vehicules": [
    {
      "id": "uuid",
      "marque": "Toyota",
      "modele": "Corolla",
      "annee": 2020,
      "immatriculation": "BJ-1234-A",
      "couleur": "Blanc",
      "type_vehicule": "BERLINE",
      "nombre_places": 4,
      "climatise": true,
      "photo_url": null,
      "actif": true
    }
  ]
}
```

```json
// 403 — si l'utilisateur n'a pas le rôle CHAUFFEUR
{ "detail": "Permission refusée" }
```

---

### 9. Modifier mon profil chauffeur

```
PATCH /chauffeurs/me
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

**Corps** — tous optionnels

```json
{
  "cin_numero": "BJ9999999",
  "permis_numero": "P000001",
  "permis_expiration": "2030-06-15"
}
```

**Réponse 200** : profil chauffeur mis à jour

---

### 10. Upload documents KYC

```
POST /chauffeurs/me/documents
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
Content-Type: multipart/form-data
```

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `cin` | fichier | Non | Photo de la CIN (recto) |
| `permis` | fichier | Non | Photo du permis de conduire |
| `casier_judiciaire` | fichier | Non | Extrait du casier judiciaire |

> Envoyer au moins un fichier. Types acceptés : JPEG, PNG, WebP — max 5 Mo chacun.  
> L'admin valide ensuite le KYC (`kyc_valide` passe à `true`).

**Réponse 200** : profil chauffeur mis à jour avec les URLs de documents

---

### 11. Passer en ligne / hors ligne

```
POST /chauffeurs/me/online
POST /chauffeurs/me/offline
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

> Le chauffeur doit avoir `kyc_valide = true` pour passer en ligne.  
> **Prérequis pour publier un trajet** : être en ligne.

```json
// 200 OK
{ "message": "Vous êtes maintenant en ligne" }
{ "message": "Vous êtes maintenant hors ligne" }

// 403 — KYC non validé
{ "detail": "KYC non validé" }
```

---

### 12. Mettre à jour la position GPS

```
POST /chauffeurs/me/position
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

**Corps**

```json
{
  "lat": 6.3703,
  "lng": 2.3912,
  "vitesse": 68.5,
  "heading": 45.0
}
```

| Champ | Type | Obligatoire | Contrainte |
|---|---|---|---|
| `lat` | float | Oui | -90 à 90 |
| `lng` | float | Oui | -180 à 180 |
| `vitesse` | float | Non | km/h |
| `heading` | float | Non | degrés (0–360) |

**Réponse 204** — pas de corps.  
> Si un voyage `EN_COURS` est actif, la position est broadcastée en temps réel via WebSocket aux passagers.

---

### 13. Statistiques & revenus

```
GET /chauffeurs/me/stats
GET /chauffeurs/me/revenus
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

**Réponse stats**

```json
{
  "nombre_trajets": 142,
  "revenus_total": 710000,
  "note_moyenne": 4.7,
  "nombre_avis": 89,
  "en_ligne": false
}
```

**Réponse revenus**

```json
{
  "aujourd_hui": 15000,
  "semaine": 87000,
  "mois": 320000,
  "total": 710000
}
```

---

### 14. Gestion des véhicules

#### Lister mes véhicules

```
GET /chauffeurs/me/vehicules
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

**Réponse 200** : liste des véhicules actifs (voir structure dans §8)

#### Ajouter un véhicule

```
POST /chauffeurs/me/vehicules
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

```json
{
  "marque": "Toyota",
  "modele": "Corolla",
  "annee": 2020,
  "immatriculation": "BJ-1234-A",
  "couleur": "Blanc",
  "type_vehicule": "BERLINE",
  "nombre_places": 4,
  "climatise": true
}
```

| Champ | Type | Contrainte |
|---|---|---|
| `annee` | int | 2000 à 2030 |
| `type_vehicule` | string | `BERLINE` \| `SUV` \| `MINIBUS` \| `BUS` \| `MOTO` |
| `nombre_places` | int | 1 à 20 |

**Réponse 201** : véhicule créé

```json
// 409 — immatriculation déjà enregistrée
{ "detail": "Immatriculation déjà enregistrée" }
```

#### Modifier un véhicule

```
PATCH /chauffeurs/me/vehicules/{vehicule_id}
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

**Corps** — tous optionnels

```json
{
  "couleur": "Rouge",
  "nombre_places": 5,
  "climatise": false
}
```

#### Supprimer un véhicule

```
DELETE /chauffeurs/me/vehicules/{vehicule_id}
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

Suppression logique (`actif = false`).

**Réponse 200**

```json
{ "message": "Véhicule supprimé" }
```

---

### 15. Profil public d'un chauffeur

```
GET /chauffeurs/{chauffeur_id}
Authorization: Bearer <access_token>
```

**Réponse 200** — informations publiques uniquement

```json
{
  "id": "uuid",
  "nom": "Dupont",
  "prenom": "Marc",
  "photo_url": "https://...",
  "note_moyenne": 4.7,
  "nombre_avis": 89,
  "nombre_trajets": 142,
  "en_ligne": true
}
```

#### Voyages d'un chauffeur

```
GET /chauffeurs/{chauffeur_id}/voyages
Authorization: Bearer <access_token>
```

**Réponse 200** : liste de voyages PUBLIE / EN_COURS (voir structure Voyage §17)

---

## VOYAGES

### 16. Publier un trajet

```
POST /voyages
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

> **Prérequis** : KYC validé + être en ligne + avoir un véhicule actif.

**Corps**

```json
{
  "ville_depart": "Cotonou",
  "ville_arrivee": "Parakou",
  "point_depart": "Gare de Cotonou, Quartier Gbégamey",
  "point_arrivee": "Gare de Parakou, Rue des Routiers",
  "lat_depart": 6.3703,
  "lng_depart": 2.3912,
  "lat_arrivee": 9.3372,
  "lng_arrivee": 2.6281,
  "date_depart": "2026-05-10T07:00:00Z",
  "prix_par_place": 5000,
  "nombre_places_total": 4,
  "vehicule_id": "uuid-du-vehicule",
  "accepte_colis": true,
  "climatise": true,
  "non_fumeur": true
}
```

| Champ | Type | Obligatoire | Contrainte |
|---|---|---|---|
| `ville_depart` | string | Oui | — |
| `ville_arrivee` | string | Oui | — |
| `point_depart` | string | Oui | Adresse précise du point de départ |
| `point_arrivee` | string | Oui | Adresse précise du point d'arrivée |
| `lat_depart` | float | Oui | Latitude GPS |
| `lng_depart` | float | Oui | Longitude GPS |
| `lat_arrivee` | float | Oui | Latitude GPS |
| `lng_arrivee` | float | Oui | Longitude GPS |
| `date_depart` | datetime | Oui | ISO 8601 avec timezone (UTC recommandé) |
| `prix_par_place` | int | Oui | 500 à 100 000 FCFA |
| `nombre_places_total` | int | Oui | 1 à 8 |
| `vehicule_id` | uuid | Oui | Doit appartenir au chauffeur et être actif |
| `accepte_colis` | bool | Non | Défaut : `true` |
| `climatise` | bool | Non | Défaut : `false` |
| `non_fumeur` | bool | Non | Défaut : `true` |

**Réponse 201**

```json
{
  "id": "uuid",
  "chauffeur_id": "uuid",
  "vehicule_id": "uuid",
  "ville_depart": "Cotonou",
  "ville_arrivee": "Parakou",
  "point_depart": "Gare de Cotonou, Quartier Gbégamey",
  "point_arrivee": "Gare de Parakou, Rue des Routiers",
  "date_depart": "2026-05-10T07:00:00Z",
  "date_arrivee_estimee": "2026-05-10T07:00:00Z",
  "prix_par_place": 5000,
  "nombre_places_restantes": 4,
  "nombre_places_total": 4,
  "accepte_colis": true,
  "climatise": true,
  "non_fumeur": true,
  "statut": "PUBLIE",
  "distance_km": null,
  "created_at": "2026-04-28T14:00:00Z"
}
```

```json
// 403 — hors ligne ou KYC non validé
{
  "error": { "code": "KYC_NOT_VALIDATED", "message": "KYC non validé, veuillez contacter le support" }
}
{ "detail": "Vous devez être en ligne pour publier un trajet" }
```

---

### 17. Détail d'un voyage

```
GET /voyages/{voyage_id}
Authorization: Bearer <access_token>
```

**Réponse 200** : même structure que la réponse de création (§16)

```json
// 404
{ "detail": "Voyage introuvable" }
```

---

### 18. Rechercher des trajets

```
GET /voyages/search
Authorization: Bearer <access_token>
```

**Paramètres de requête**

| Paramètre | Type | Obligatoire | Description |
|---|---|---|---|
| `ville_depart` | string | Oui | Recherche partielle (insensible à la casse) |
| `ville_arrivee` | string | Oui | Recherche partielle (insensible à la casse) |
| `date_depart` | date | Oui | Format `YYYY-MM-DD` — filtre sur la journée complète |
| `nombre_places` | int | Non | Défaut : 1 — minimum de places disponibles |
| `accepte_colis` | bool | Non | Filtrer les trajets qui acceptent des colis |
| `climatise` | bool | Non | Filtrer les véhicules climatisés |
| `prix_max` | int | Non | Prix maximum par place en FCFA |
| `sort_by` | string | Non | `depart_asc` (défaut) \| `depart_desc` \| `prix_asc` \| `prix_desc` |
| `page` | int | Non | Défaut : 1 |
| `size` | int | Non | Défaut : 20 — max : 100 |

**Exemple**

```
GET /voyages/search?ville_depart=Cotonou&ville_arrivee=Parakou&date_depart=2026-05-10&nombre_places=2&climatise=true&sort_by=prix_asc
```

**Réponse 200**

```json
{
  "items": [ /* liste de VoyageRead */ ],
  "total": 8,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

---

### 19. Trajets populaires (page d'accueil)

```
GET /voyages/popular
```

> Endpoint **public** — aucune authentification requise. Retourne les 10 prochains voyages PUBLIE triés par date de départ.

**Réponse 200** : liste de voyages (même structure §16)

---

### 20. Mes trajets publiés (chauffeur)

```
GET /voyages/me
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

**Réponse 200** : liste de tous les voyages du chauffeur (tous statuts, triés par date décroissante)

---

### 21. Modifier un trajet

```
PATCH /voyages/{voyage_id}
Authorization: Bearer <access_token>   (rôle CHAUFFEUR, propriétaire)
```

> Seul un voyage en statut `PUBLIE` peut être modifié.

**Corps** — tous optionnels

```json
{
  "prix_par_place": 6000,
  "point_depart": "Nouveau point de départ",
  "date_depart": "2026-05-10T08:00:00Z",
  "accepte_colis": false,
  "non_fumeur": true
}
```

**Réponse 200** : voyage mis à jour

```json
// 400 — statut invalide
{ "detail": "Seul un voyage PUBLIE peut être modifié" }
// 403 — pas propriétaire
{ "detail": "Ce voyage ne vous appartient pas" }
```

---

### 22. Démarrer / Terminer / Annuler un trajet

```
POST /voyages/{voyage_id}/start
POST /voyages/{voyage_id}/end
POST /voyages/{voyage_id}/cancel
Authorization: Bearer <access_token>   (rôle CHAUFFEUR, propriétaire)
```

| Action | Statut requis | Nouveau statut | Effet sur réservations |
|---|---|---|---|
| `start` | `PUBLIE` ou `COMPLET` | `EN_COURS` | Aucun |
| `end` | `EN_COURS` | `TERMINE` | CONFIRMEE → TERMINEE |
| `cancel` | `PUBLIE` ou `COMPLET` | `ANNULE` | EN_ATTENTE + CONFIRMEE → ANNULEE |

**Réponse 200**

```json
{ "message": "Voyage démarré" }
{ "message": "Voyage terminé" }
{ "message": "Voyage annulé" }
```

```json
// 400 — transition invalide
{ "detail": "Seul un voyage PUBLIE ou COMPLET peut être démarré" }
// 403 — pas propriétaire
{ "detail": "Ce voyage ne vous appartient pas" }
```

---

### 23. Liste des passagers confirmés

```
GET /voyages/{voyage_id}/passagers
Authorization: Bearer <access_token>   (rôle CHAUFFEUR, propriétaire)
```

**Réponse 200** : liste des réservations avec statut `CONFIRMEE` (voir structure Réservation §24)

---

## RÉSERVATIONS

### 24. Créer une réservation

```
POST /reservations
Authorization: Bearer <access_token>
```

> Disponible pour tous les rôles. Un chauffeur ne peut pas réserver sur son propre voyage.

**Corps**

```json
{
  "voyage_id": "uuid-du-voyage",
  "nombre_places": 2
}
```

| Champ | Type | Contrainte |
|---|---|---|
| `nombre_places` | int | 1 à 8 |

**Réponse 201**

```json
{
  "id": "uuid",
  "voyage_id": "uuid",
  "client_id": "uuid",
  "nombre_places": 2,
  "prix_total": 10000,
  "statut": "EN_ATTENTE",
  "code_confirmation": "A3F9B2",
  "created_at": "2026-04-28T14:30:00Z"
}
```

> `prix_total` = `prix_par_place × nombre_places`. Calculé automatiquement côté serveur.  
> `code_confirmation` est un code à 6 caractères hexadécimaux — à afficher au client pour présentation au chauffeur.

```json
// 409 — places insuffisantes ou voyage COMPLET/ANNULE
{ "detail": "Places insuffisantes" }
{ "detail": "Ce voyage n'accepte plus de réservations" }

// 403 — chauffeur réservant son propre voyage
{ "detail": "Vous ne pouvez pas réserver sur votre propre voyage" }
```

---

### 25. Mes réservations (client)

```
GET /reservations/me
Authorization: Bearer <access_token>
```

**Réponse 200** : liste de toutes mes réservations triées par date décroissante

```json
[
  {
    "id": "uuid",
    "voyage_id": "uuid",
    "client_id": "uuid",
    "nombre_places": 2,
    "prix_total": 10000,
    "statut": "CONFIRMEE",
    "code_confirmation": "A3F9B2",
    "created_at": "2026-04-28T14:30:00Z"
  }
]
```

---

### 26. Réservations en attente (chauffeur)

```
GET /reservations/me/incoming
Authorization: Bearer <access_token>   (rôle CHAUFFEUR)
```

> Retourne toutes les réservations `EN_ATTENTE` sur les voyages du chauffeur, triées par date décroissante. À appeler régulièrement ou après notification push.

**Réponse 200** : même structure que §25

---

### 27. Détail d'une réservation

```
GET /reservations/{reservation_id}
Authorization: Bearer <access_token>
```

> Accessible uniquement par le client propriétaire ou le chauffeur du voyage concerné.

**Réponse 200** : voir structure §24

```json
// 403 — accès non autorisé
{ "detail": "Accès non autorisé" }
// 404
{ "detail": "Réservation introuvable" }
```

---

### 28. Accepter une réservation (chauffeur)

```
POST /reservations/{reservation_id}/accept
Authorization: Bearer <access_token>   (rôle CHAUFFEUR, propriétaire du voyage)
```

> Passe la réservation de `EN_ATTENTE` à `CONFIRMEE`.

**Réponse 200**

```json
{ "message": "Réservation acceptée" }
```

```json
// 400 — déjà acceptée ou dans un autre état
{ "detail": "Seule une réservation EN_ATTENTE peut être acceptée" }
// 403 — réservation sur un autre voyage
{ "detail": "Cette réservation ne concerne pas votre voyage" }
```

---

### 29. Refuser une réservation (chauffeur)

```
POST /reservations/{reservation_id}/reject
Authorization: Bearer <access_token>   (rôle CHAUFFEUR, propriétaire du voyage)
```

> Passe la réservation à `REFUSEE`. Les places sont **restituées** automatiquement sur le voyage.

**Réponse 200**

```json
{ "message": "Réservation refusée" }
```

---

### 30. Annuler une réservation

```
POST /reservations/{reservation_id}/cancel
Authorization: Bearer <access_token>
```

> Accessible par le **client** (propriétaire) ou le **chauffeur** (propriétaire du voyage).  
> Les places sont **restituées** automatiquement. Si le voyage était `COMPLET`, il repasse en `PUBLIE`.

| Statut avant | Statut après | Annulable |
|---|---|---|
| `EN_ATTENTE` | `ANNULEE` | Oui |
| `CONFIRMEE` | `ANNULEE` | Oui |
| `REFUSEE` | — | Non |
| `TERMINEE` | — | Non |
| `ANNULEE` | — | Non |

**Réponse 200**

```json
{ "message": "Réservation annulée" }
```

```json
// 400 — état non annulable
{ "detail": "Réservation non annulable dans cet état" }
```

---

## Statuts et cycles de vie

### Statuts d'un voyage

```
PUBLIE ──┬── (réservations jusqu'à saturation) ──► COMPLET
         │                                              │
         ├── start ──────────────────────────────────► EN_COURS ──► end ──► TERMINE
         │   (PUBLIE ou COMPLET)                        
         └── cancel ──────────────────────────────────► ANNULE
             (PUBLIE ou COMPLET)
```

### Statuts d'une réservation

```
EN_ATTENTE ──┬── accept (chauffeur) ──► CONFIRMEE ──── voyage end ──► TERMINEE
             ├── reject (chauffeur) ──► REFUSEE          │
             └── cancel             ──► ANNULEE      cancel ────────► ANNULEE
```

---

## Flux recommandé — Application mobile

### Côté client

```
1.  register() / login()           → stocker access_token + refresh_token
2.  otp/send() + otp/verify()      → telephone_verifie = true
3.  GET /voyages/popular            → afficher page d'accueil sans auth
4.  GET /voyages/search?...         → rechercher un trajet
5.  GET /voyages/{id}               → détail avant réservation
6.  POST /reservations              → réserver (statut EN_ATTENTE)
7.  [notification push]             → réservation acceptée ou refusée
8.  GET /reservations/me            → liste de mes réservations
9.  POST /reservations/{id}/cancel  → annuler si besoin
```

### Côté chauffeur

```
1.  register() / login()                    → stocker tokens
2.  POST /chauffeurs/me/documents           → uploader CIN + permis (KYC admin)
3.  [notification push]                     → KYC validé
4.  POST /chauffeurs/me/vehicules           → ajouter un véhicule
5.  POST /chauffeurs/me/online              → passer en ligne
6.  POST /voyages                           → publier un trajet
7.  [notification push]                     → nouvelle réservation
8.  GET /reservations/me/incoming           → voir les demandes EN_ATTENTE
9.  POST /reservations/{id}/accept          → accepter
10. POST /voyages/{id}/start                → démarrer le trajet
11. POST /chauffeurs/me/position (loop)     → envoyer position GPS toutes les 3 sec
12. POST /voyages/{id}/end                  → terminer le trajet
13. POST /chauffeurs/me/offline             → passer hors ligne
```

---

## Format des erreurs

Toutes les erreurs métier suivent ce format uniforme :

```json
{
  "error": {
    "code": "CODE_ERREUR",
    "message": "Description lisible",
    "details": {},
    "request_id": "uuid-de-la-requête"
  }
}
```

Les erreurs de validation Pydantic (422) retournent le format standard FastAPI :

```json
{
  "detail": [
    {
      "loc": ["body", "nombre_places"],
      "msg": "Input should be less than or equal to 8",
      "type": "less_than_equal"
    }
  ]
}
```

| Code | HTTP | Description |
|---|---|---|
| `KYC_NOT_VALIDATED` | 403 | KYC non validé — chauffeur ne peut pas publier |
| `PERMISSION_DENIED` | 403 | Action non autorisée pour ce rôle |
| `VOYAGE_NOT_FOUND` | 404 | Voyage introuvable |
| `USER_NOT_FOUND` | 404 | Utilisateur introuvable |

---

## Infrastructure active

| Service | Hôte | Port |
|---|---|---|
| API GoTaxi | localhost | 8001 |
| PostgreSQL | localhost | 5439 |
| Redis | localhost | 6380 |
| pgAdmin | localhost | 5051 |

> Tests : **82/82 passent** — `pytest tests/integration/`