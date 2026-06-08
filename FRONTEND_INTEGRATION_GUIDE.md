# Guide d'intégration Frontend — GoTaxi API

**Base URL:** `https://<domaine>/api/v1`  
**Docs interactives:** `GET /docs` (Swagger) · `GET /redoc`

---

## 1. Authentification

Toutes les routes sauf `/auth/register`, `/auth/login` et `/voyages/search` nécessitent le header :

```
Authorization: Bearer <access_token>
```

### Inscription client

```http
POST /auth/register
Content-Type: application/json

{
  "telephone": "+22961000000",
  "nom": "Kpan",
  "prenom": "Ariel",
  "password": "motdepasse8+"
}
```

> Format téléphone : `+229` + 10 chiffres (Bénin) ou `+228` + 8 chiffres (Togo).

**Réponse 201 :** `{ "message": "Inscription réussie. Vérifiez votre téléphone." }`

Après inscription → vérifier le téléphone par OTP avant de pouvoir se connecter.

### Vérification OTP

```http
POST /auth/otp/send
{ "telephone": "+22961000000" }

POST /auth/otp/verify
{ "telephone": "+22961000000", "code": "123456" }
```

### Connexion

```http
POST /auth/login

{
  "telephone": "+22961000000",
  "password": "motdepasse8+"
}
```

**Réponse :**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

L'`access_token` expire en **30 min**. Rafraîchir avant expiration :

```http
POST /auth/refresh
{ "refresh_token": "eyJ..." }
```

> **Bonne pratique :** implémenter un intercepteur HTTP qui appelle `/auth/refresh` automatiquement sur un 401 et rejoue la requête initiale.

### Déconnexion

```http
POST /auth/logout
Authorization: Bearer <token>
```

### Mot de passe oublié

```http
POST /auth/password/forgot
{ "telephone": "+22961000000" }

POST /auth/password/reset
{ "telephone": "+22961000000", "code": "123456", "new_password": "nouveaumdp8+" }
```

---

## 2. Réservation de place — Côté Client

### Étape 1 — Rechercher un voyage

```http
GET /voyages/search?ville_depart=Cotonou&ville_arrivee=Parakou&date_depart=2026-05-20&nombre_places=2
Authorization: Bearer <token>
```

| Paramètre | Type | Obligatoire | Description |
|-----------|------|-------------|-------------|
| `ville_depart` | string | oui | Recherche partielle (ilike) |
| `ville_arrivee` | string | oui | Recherche partielle (ilike) |
| `date_depart` | date `YYYY-MM-DD` | oui | |
| `nombre_places` | int ≥ 1 | non (défaut 1) | |
| `accepte_colis` | bool | non | |
| `climatise` | bool | non | |
| `prix_max` | int (XOF) | non | |
| `sort_by` | string | non | `depart_asc` (défaut) · `depart_desc` · `prix_asc` · `prix_desc` |
| `page` | int ≥ 1 | non (défaut 1) | |
| `size` | int 1–100 | non (défaut 20) | |

**Réponse :**

```json
{
  "items": [
    {
      "id": "uuid",
      "chauffeur_id": "uuid",
      "vehicule_id": "uuid",
      "ville_depart": "Cotonou",
      "ville_arrivee": "Parakou",
      "point_depart": "Gare Jonquet",
      "point_arrivee": "Gare Parakou",
      "date_depart": "2026-05-20T07:00:00Z",
      "date_arrivee_estimee": "2026-05-20T12:00:00Z",
      "prix_par_place": 3000,
      "nombre_places_restantes": 3,
      "nombre_places_total": 4,
      "accepte_colis": true,
      "climatise": false,
      "non_fumeur": true,
      "statut": "PUBLIE",
      "distance_km": 420,
      "created_at": "..."
    }
  ],
  "total": 5,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

> **Statuts de voyage possibles :** `PUBLIE` · `COMPLET` · `EN_COURS` · `TERMINE` · `ANNULE`  
> La recherche ne retourne que les voyages `PUBLIE`.

### Étape 2 — Créer la réservation

```http
POST /reservations
Authorization: Bearer <token>
Content-Type: application/json

{
  "voyage_id": "uuid-du-voyage",
  "nombre_places": 2
}
```

> Contraintes : `nombre_places` entre 1 et 8, places disponibles suffisantes, voyage `PUBLIE`, le chauffeur ne peut pas réserver son propre voyage.

**Réponse 201 :**

```json
{
  "id": "uuid-reservation",
  "voyage_id": "...",
  "client_id": "...",
  "nombre_places": 2,
  "prix_total": 6000,
  "statut": "EN_ATTENTE",
  "code_confirmation": "A3F9BC",
  "created_at": "...",
  "voyage": { "...": "objet VoyageRead complet" }
}
```

> **Cycle de vie d'une réservation :**
> ```
> EN_ATTENTE → CONFIRMEE → TERMINEE
>           ↘ REFUSEE
>           ↘ ANNULEE (client ou chauffeur)
> ```

### Étape 3 — Suivre ses réservations

```http
GET /reservations/me           // historique complet
GET /reservations/{id}         // détail (embed voyage + client)
```

### Étape 4 — Annuler

```http
POST /reservations/{id}/cancel
Authorization: Bearer <token>
```

> Possible uniquement sur les statuts `EN_ATTENTE` et `CONFIRMEE`. Les places sont automatiquement restituées au voyage.

---

## 3. Réservation de place — Côté Chauffeur

### Voir les demandes entrantes

```http
GET /reservations/me/incoming
Authorization: Bearer <token>   // rôle CHAUFFEUR requis
```

Retourne les réservations `EN_ATTENTE` et `CONFIRMEE` sur tous les voyages du chauffeur, avec l'objet `client` (nom, prénom, téléphone) intégré.

### Accepter / Refuser une demande

```http
POST /reservations/{id}/accept   // EN_ATTENTE → CONFIRMEE
POST /reservations/{id}/reject   // EN_ATTENTE → REFUSEE (places restituées)
```

### Gérer le voyage

```http
// Lister toutes les réservations d'un voyage (filtre optionnel par statut)
GET /voyages/{voyage_id}/reservations?statut=CONFIRMEE
Authorization: Bearer <token>

// Passagers confirmés uniquement
GET /voyages/{voyage_id}/passagers

// Démarrer le voyage (PUBLIE ou COMPLET → EN_COURS)
POST /voyages/{voyage_id}/start

// Terminer le voyage (EN_COURS → TERMINE, toutes CONFIRMEE → TERMINEE)
POST /voyages/{voyage_id}/end

// Annuler le voyage (PUBLIE ou COMPLET → ANNULE, toutes réservations actives → ANNULEE)
POST /voyages/{voyage_id}/cancel
```

### Mes voyages

```http
GET /voyages/me
Authorization: Bearer <token>   // rôle CHAUFFEUR requis
```

---

## 4. Envoi de colis — Côté Client

### Étape 1 — Rechercher un voyage acceptant des colis

Utiliser l'endpoint dédié — il inclut aussi les voyages `COMPLET` et `EN_COURS` (le colis ne prend pas de place passager) :

```http
GET /voyages/colis-search?ville_depart=Cotonou&ville_arrivee=Parakou&date_depart=2026-05-20
Authorization: Bearer <token>
```

| Paramètre | Type | Obligatoire |
|-----------|------|-------------|
| `ville_depart` | string | oui |
| `ville_arrivee` | string | oui |
| `date_depart` | date `YYYY-MM-DD` | oui |
| `sort_by` | string | non |
| `page` / `size` | int | non |

Même format de réponse que `/voyages/search`.

### Étape 2 — Créer le colis

```http
POST /colis
Authorization: Bearer <token>
Content-Type: application/json

{
  "voyage_id": "uuid-du-voyage",
  "description": "Vêtements pour tante Rosine",
  "categorie": "VETEMENTS",
  "poids_kg": 2.5,
  "fragile": false,
  "destinataire_nom": "Rosine Adjo",
  "destinataire_telephone": "+22997000000",
  "modalite_paiement": "A_LA_LIVRAISON"
}
```

| Champ | Type | Obligatoire | Notes |
|-------|------|-------------|-------|
| `voyage_id` | UUID | oui | Voyage acceptant les colis |
| `description` | string ≤ 500 | oui | |
| `categorie` | enum | oui | Voir tableau ci-dessous |
| `poids_kg` | float 0–100 | non | |
| `fragile` | bool | non (défaut `false`) | |
| `destinataire_nom` | string ≤ 100 | oui | |
| `destinataire_telephone` | string ≤ 20 | oui | |
| `modalite_paiement` | enum | non | `A_LA_LIVRAISON` (défaut) ou `A_LA_CONFIRMATION` |

**Catégories :**

| Valeur | Coefficient tarifaire |
|--------|-----------------------|
| `DOCUMENTS` | × 0.8 |
| `VETEMENTS` | × 1.0 |
| `ALIMENTAIRE` | × 1.1 |
| `ELECTRONIQUE` | × 1.5 |
| `FRAGILE` | × 1.5 |
| `AUTRE` | × 1.0 |

**Modalités de paiement :**
- `A_LA_CONFIRMATION` — le client paie quand le chauffeur accepte le colis
- `A_LA_LIVRAISON` — le client paie à la livraison

**Réponse 201 :**

```json
{
  "id": "uuid-colis",
  "code_suivi": "GTX-A3K9F2",
  "ville_depart": "Cotonou",
  "ville_arrivee": "Parakou",
  "description": "Vêtements pour tante Rosine",
  "categorie": "VETEMENTS",
  "poids_kg": 2.5,
  "fragile": false,
  "destinataire_nom": "Rosine Adjo",
  "destinataire_telephone": "+22997000000",
  "prix": 1560.0,
  "modalite_paiement": "A_LA_LIVRAISON",
  "statut": "EN_ATTENTE",
  "photo_url": null,
  "voyage": { "...": "objet VoyageRead complet" },
  "created_at": "...",
  "updated_at": "..."
}
```

> **Tarification serveur-side (non recalculable côté front) :**
> ```
> prix = max(500, distance_km × 3 × coeff_catégorie + poids_kg × 100 + 300 si fragile)
> ```
> Afficher le `prix` retourné dans la réponse 201 et demander confirmation à l'utilisateur. En cas de refus, appeler immédiatement l'annulation.

> **Cycle de vie d'un colis :**
> ```
> EN_ATTENTE → CONFIRME → EN_TRANSIT → LIVRE
>           ↘ ANNULE
> ```

### Étape 3 — Suivre le colis

```http
GET /colis/me              // tous mes colis envoyés
GET /colis/{colis_id}      // détail avec voyage embedded
```

### Étape 4 — Annuler

```http
POST /colis/{colis_id}/annuler
Authorization: Bearer <token>
```

Possible uniquement à l'état `EN_ATTENTE`.

### WebSocket — Suivi temps réel

```
ws://<domaine>/ws/tracking/colis/{colis_id}
```

Se connecter après la création du colis. Le serveur pousse des événements JSON à chaque changement de statut. Envoyer `ping` pour maintenir la connexion, la réponse est `pong`.

---

## 5. Envoi de colis — Côté Chauffeur

```http
// Voir tous les colis d'un voyage
GET /colis/voyage/{voyage_id}
Authorization: Bearer <token>

// Accepter le colis (EN_ATTENTE → CONFIRME)
POST /colis/{colis_id}/confirmer

// Mettre en transit (CONFIRME → EN_TRANSIT) — voyage doit être EN_COURS
POST /colis/{colis_id}/en_transit

// Marquer comme livré (EN_TRANSIT → LIVRE)
POST /colis/{colis_id}/livrer

// Annuler (EN_ATTENTE → ANNULE)
POST /colis/{colis_id}/annuler
```

> **Important :** `en_transit` échoue avec 422 si le voyage n'est pas encore `EN_COURS`.  
> Ordre correct : `POST /voyages/{voyage_id}/start` → `POST /colis/{id}/en_transit`.

---

## 6. Wallet & Paiement Mobile Money

### Consulter le solde

```http
GET /wallet/me
Authorization: Bearer <token>
```

```json
{
  "id": "uuid",
  "solde": 15000,
  "devise": "XOF",
  "actif": true
}
```

### Recharger le wallet

#### Phase 1 — Initier la recharge

```http
POST /wallet/me/recharge/initiate
Authorization: Bearer <token>
Content-Type: application/json

{
  "montant": 5000,
  "operateur": "MTN_MOMO",
  "telephone": "+22961000000"
}
```

| Champ | Contrainte |
|-------|-----------|
| `montant` | 500 – 1 000 000 XOF |
| `operateur` | `MTN_MOMO` · `ORANGE_MONEY` · `MOOV_MONEY` |
| `telephone` | numéro Mobile Money de l'utilisateur |

**Réponses selon opérateur :**

```json
// MTN MoMo
{ "message": "Recharge MTN MoMo initiée. Confirmez le paiement USSD sur le +22961000000." }

// Orange Money — afficher le lien dans un WebView ou navigateur
{ "message": "Recharge Orange Money initiée. Suivez le lien de paiement fourni." }

// Moov Money
{ "message": "Recharge Moov Money initiée. Confirmez le paiement sur le +22961000000." }
```

> Pour Orange Money : si le message contient un lien de paiement, l'ouvrir dans un WebView ou dans le navigateur par défaut.

#### Phase 2 — Confirmer / Vérifier le statut

Le Celery beat poll automatiquement toutes les **60 secondes** pour MTN MoMo. Deux stratégies possibles :

**Option A — Poll passif (recommandée pour UX simple)**

```http
// Répéter toutes les 10-15s jusqu'à ce que solde augmente
GET /wallet/me
```

**Option B — Confirmation manuelle immédiate**

Récupérer l'ID de la transaction depuis l'activité :

```http
GET /wallet/me/activity?page=1&size=1
```

Prendre l'`id` de la transaction en statut `EN_ATTENTE`, puis :

```http
POST /wallet/me/recharge/confirm?transaction_id=<uuid>
Authorization: Bearer <token>
```

| Statut HTTP | Signification |
|-------------|--------------|
| 200 | Succès — retourne le wallet mis à jour (`solde` incrémenté) |
| 202 | Paiement encore en attente — réessayer dans 10-15s |
| 402 | Paiement refusé ou échoué côté opérateur |
| 502 | Erreur de communication avec l'opérateur |

### Retirer vers Mobile Money

```http
POST /wallet/me/withdraw
Authorization: Bearer <token>
Content-Type: application/json

{
  "montant": 2000,
  "telephone": "+22961000000",
  "operateur": "MTN_MOMO"
}
```

| Opérateur | Comportement |
|-----------|-------------|
| `MTN_MOMO` | Virement automatique via API — quasi-instantané |
| `ORANGE_MONEY` | Traitement manuel — afficher "traitement sous 24h" |
| `MOOV_MONEY` | Traitement manuel — afficher "traitement sous 24h" |

### Transfert wallet vers wallet

```http
POST /wallet/me/transfer
Authorization: Bearer <token>
Content-Type: application/json

{
  "destinataire_telephone": "+22965000000",
  "montant": 1000
}
```

> `montant` minimum : 100 XOF. Le destinataire doit avoir un compte GoTaxi actif.

### Historique des transactions

```http
GET /wallet/me/activity?page=1&size=20
Authorization: Bearer <token>
```

```json
{
  "items": [
    {
      "id": "uuid",
      "type": "RECHARGE",
      "statut": "REUSSI",
      "operateur": "MTN_MOMO",
      "montant": 5000,
      "created_at": "2026-05-10T14:32:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

**Types de transactions :** `RECHARGE` · `PAIEMENT_VOYAGE` · `PAIEMENT_COLIS` · `REVERSEMENT` · `REMBOURSEMENT` · `COMMISSION`

**Statuts :** `EN_ATTENTE` · `EN_COURS` · `REUSSI` · `ECHEC` · `ANNULE`

---

## 7. WebSocket — Suivi GPS Voyage

```
ws://<domaine>/ws/tracking/voyage/{voyage_id}
```

Utile pour afficher la position du chauffeur en temps réel pendant le voyage (`EN_COURS`). Envoyer `ping` périodiquement, réponse `pong`.

---

## 8. Codes d'erreur

| HTTP | Cause fréquente |
|------|----------------|
| 400 | Action impossible sur l'état actuel (ex : accepter une réservation déjà confirmée) |
| 401 | Token absent, expiré ou révoqué → appeler `/auth/refresh` |
| 402 | Solde insuffisant ou paiement Mobile Money refusé |
| 403 | Action sur une ressource qui n'appartient pas à l'utilisateur connecté |
| 404 | Ressource introuvable |
| 409 | Conflit d'état (ex : plus de places disponibles au moment de la réservation) |
| 422 | Données invalides — lire `detail` pour le champ en erreur |
| 502 | Erreur de communication avec l'opérateur Mobile Money |

**Format d'erreur standard :**

```json
{ "detail": "Message d'erreur lisible" }
```

---

## 9. Tableau récapitulatif des routes

### Authentification

| Action | Méthode | URL |
|--------|---------|-----|
| Inscription client | POST | `/auth/register` |
| Inscription chauffeur | POST | `/auth/register/chauffeur` |
| Connexion | POST | `/auth/login` |
| Rafraîchir token | POST | `/auth/refresh` |
| Déconnexion | POST | `/auth/logout` |
| Envoyer OTP | POST | `/auth/otp/send` |
| Vérifier OTP | POST | `/auth/otp/verify` |
| Mot de passe oublié | POST | `/auth/password/forgot` |
| Réinitialiser mot de passe | POST | `/auth/password/reset` |

### Voyages

| Action | Méthode | URL |
|--------|---------|-----|
| Recherche (passagers) | GET | `/voyages/search` |
| Recherche (colis) | GET | `/voyages/colis-search` |
| Détail d'un voyage | GET | `/voyages/{id}` |
| Mes voyages (chauffeur) | GET | `/voyages/me` |
| Démarrer le voyage | POST | `/voyages/{id}/start` |
| Terminer le voyage | POST | `/voyages/{id}/end` |
| Annuler le voyage | POST | `/voyages/{id}/cancel` |
| Réservations du voyage | GET | `/voyages/{id}/reservations` |
| Passagers confirmés | GET | `/voyages/{id}/passagers` |

### Réservations

| Action | Méthode | URL |
|--------|---------|-----|
| Créer une réservation | POST | `/reservations` |
| Mes réservations | GET | `/reservations/me` |
| Demandes entrantes (chauffeur) | GET | `/reservations/me/incoming` |
| Détail | GET | `/reservations/{id}` |
| Accepter | POST | `/reservations/{id}/accept` |
| Refuser | POST | `/reservations/{id}/reject` |
| Annuler | POST | `/reservations/{id}/cancel` |

### Colis

| Action | Méthode | URL |
|--------|---------|-----|
| Créer un colis | POST | `/colis` |
| Mes colis | GET | `/colis/me` |
| Détail | GET | `/colis/{id}` |
| Colis d'un voyage (chauffeur) | GET | `/colis/voyage/{voyage_id}` |
| Confirmer (chauffeur) | POST | `/colis/{id}/confirmer` |
| Mettre en transit (chauffeur) | POST | `/colis/{id}/en_transit` |
| Marquer livré (chauffeur) | POST | `/colis/{id}/livrer` |
| Annuler | POST | `/colis/{id}/annuler` |

### Wallet

| Action | Méthode | URL |
|--------|---------|-----|
| Solde | GET | `/wallet/me` |
| Initier recharge | POST | `/wallet/me/recharge/initiate` |
| Confirmer recharge | POST | `/wallet/me/recharge/confirm?transaction_id=` |
| Retrait | POST | `/wallet/me/withdraw` |
| Transfert | POST | `/wallet/me/transfer` |
| Historique transactions | GET | `/wallet/me/activity` |

### WebSocket

| Canal | URL |
|-------|-----|
| Suivi GPS voyage | `ws://<domaine>/ws/tracking/voyage/{voyage_id}` |
| Suivi statut colis | `ws://<domaine>/ws/tracking/colis/{colis_id}` |

---

## 10. Points d'attention

1. **Format téléphone :** `+229XXXXXXXXXX` (Bénin, 10 chiffres après l'indicatif) ou `+228XXXXXXXX` (Togo, 8 chiffres). Le front doit normaliser ce format avant tout appel API.

2. **Devise :** tout est en **XOF (FCFA)**. Ne jamais convertir ou afficher une autre monnaie.

3. **Prix colis :** calculé côté serveur à la création — afficher le `prix` de la réponse 201 et demander une confirmation explicite avant que l'utilisateur ne puisse annuler.

4. **Recharge Orange Money :** si le champ `payment_url` est présent dans le message de réponse, l'ouvrir dans un WebView ou dans le navigateur natif.

5. **Token management :** l'`access_token` dure 30 min. Sauvegarder le `refresh_token` de façon sécurisée (Keychain iOS / Keystore Android) et intercepter les 401 pour relancer le refresh automatiquement.

6. **KYC chauffeur :** un chauffeur avec `kyc_valide: false` ne peut pas publier de voyage. Vérifier ce flag après login côté chauffeur et guider vers l'écran de validation KYC si nécessaire.

7. **Colis `en_transit` :** ce statut n'est accessible que si le voyage est `EN_COURS`. Ordonner les appels : `start voyage` → `en_transit colis`.