# GoTaxi API — Authentification · Prêt à consommer

> **Base URL** : `http://<host>:8001/api/v1`  
> **Documentation interactive** : `http://<host>:8001/docs`  
> **Format** : JSON — `Content-Type: application/json`  
> **Authentification** : Bearer JWT — `Authorization: Bearer <access_token>`

---

## Statut des endpoints

| Endpoint | Méthode | Statut |
|---|---|---|
| `/auth/register` | POST | ✅ Prêt |
| `/auth/login` | POST | ✅ Prêt |
| `/auth/logout` | POST | ✅ Prêt |
| `/auth/refresh` | POST | ✅ Prêt |
| `/auth/otp/send` | POST | ✅ Prêt (SMS Twilio : brancher clés) |
| `/auth/otp/verify` | POST | ✅ Prêt |
| `/auth/password/forgot` | POST | ✅ Prêt (SMS Twilio : brancher clés) |
| `/auth/password/reset` | POST | ✅ Prêt |
| `/auth/password/change` | POST | ✅ Prêt |

---

## 1. Inscription

```
POST /auth/register
```

### Corps de la requête

```json
{
  "telephone": "+22997000010",
  "nom": "Koffi",
  "prenom": "Marc",
  "password": "motdepasse123",
  "email": "marc@example.com"
}
```

| Champ | Type | Obligatoire | Contrainte |
|---|---|---|---|
| `telephone` | string | Oui | Format `+229XXXXXXXXXX` — 10 chiffres (Bénin) ou `+228XXXXXXXX` — 8 chiffres (Togo) |
| `nom` | string | Oui | 2 à 100 caractères |
| `prenom` | string | Oui | 2 à 100 caractères |
| `password` | string | Oui | Minimum 8 caractères |
| `email` | string | Non | — |

### Réponses

```json
// 201 Created
{ "message": "Inscription réussie. Vérifiez votre téléphone." }

// 409 Conflict — numéro déjà utilisé
{
  "error": {
    "code": "PHONE_ALREADY_EXISTS",
    "message": "Ce numéro de téléphone est déjà enregistré"
  }
}

// 422 Unprocessable — validation échouée (format téléphone, mot de passe trop court...)
```

---

## 2. Connexion

```
POST /auth/login
```

### Corps de la requête

```json
{
  "telephone": "+22997000010",
  "password": "motdepasse123"
}
```

### Réponse

```json
// 200 OK
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

> `access_token` expire dans **30 minutes** (`expires_in` = 1800 secondes).  
> `refresh_token` expire dans **30 jours**.

```json
// 401 — identifiants invalides
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Identifiants invalides"
  }
}

// 403 — compte suspendu
{
  "error": {
    "code": "ACCOUNT_SUSPENDED",
    "message": "Compte suspendu"
  }
}
```

---

## 3. Déconnexion

```
POST /auth/logout
Authorization: Bearer <access_token>
```

Révoque le token côté serveur (blacklist Redis). Toute requête ultérieure avec ce token retourne 401.

### Réponse

```json
// 200 OK
{ "message": "Déconnexion réussie" }

// 401 — token absent ou déjà révoqué
```

---

## 4. Renouvellement du token

```
POST /auth/refresh
```

À appeler quand l'`access_token` est expiré.

### Corps de la requête

```json
{
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Réponse

```json
// 200 OK — nouveaux tokens émis
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}

// 401 — refresh token invalide ou expiré
{
  "error": {
    "code": "TOKEN_INVALID",
    "message": "Token invalide ou révoqué"
  }
}
```

---

## 5. Envoi OTP (vérification du téléphone)

```
POST /auth/otp/send
```

Génère et stocke un code OTP à 6 chiffres valable **5 minutes**.  
> SMS envoyé via Twilio dès que les clés sont configurées dans `.env`.

### Corps de la requête

```json
{ "telephone": "+22997000010" }
```

### Réponse

```json
// 200 OK
{ "message": "Code OTP envoyé" }
```

---

## 6. Vérification OTP

```
POST /auth/otp/verify
```

Active le flag `telephone_verifie` de l'utilisateur si le code est correct.

### Corps de la requête

```json
{
  "telephone": "+22997000010",
  "code": "847291"
}
```

### Réponses

```json
// 200 OK
{ "message": "Téléphone vérifié" }

// 400 — code invalide
{
  "error": {
    "code": "INVALID_OTP",
    "message": "Code OTP invalide ou expiré"
  }
}

// 429 — trop de tentatives (compte bloqué 30 min)
{
  "error": {
    "code": "OTP_MAX_ATTEMPTS",
    "message": "Trop de tentatives OTP, compte bloqué 30 min"
  }
}
```

---

## 7. Mot de passe oublié

```
POST /auth/password/forgot
```

Génère un OTP et l'envoie par SMS si le numéro est enregistré.  
La réponse est **identique qu'il existe ou non** pour éviter l'énumération.

### Corps de la requête

```json
{ "telephone": "+22997000010" }
```

### Réponse

```json
// 200 OK (toujours, même si numéro inconnu)
{ "message": "Si ce numéro est enregistré, un code vous a été envoyé" }
```

---

## 8. Réinitialisation du mot de passe

```
POST /auth/password/reset
```

### Corps de la requête

```json
{
  "telephone": "+22997000010",
  "code": "847291",
  "new_password": "nouveaumdp2024"
}
```

### Réponses

```json
// 200 OK
{ "message": "Mot de passe réinitialisé" }

// 400 — code OTP invalide
// 404 — utilisateur introuvable
```

---

## 9. Changement de mot de passe

```
POST /auth/password/change
Authorization: Bearer <access_token>
```

### Corps de la requête

```json
{
  "current_password": "motdepasse123",
  "new_password": "nouveaumdp2024"
}
```

### Réponses

```json
// 200 OK
{ "message": "Mot de passe modifié" }

// 401 — mot de passe actuel incorrect
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Identifiants invalides"
  }
}
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

| Code | HTTP | Description |
|---|---|---|
| `PHONE_ALREADY_EXISTS` | 409 | Numéro déjà enregistré |
| `INVALID_CREDENTIALS` | 401 | Identifiants ou mot de passe invalides |
| `ACCOUNT_SUSPENDED` | 403 | Compte suspendu par un admin |
| `TOKEN_INVALID` | 401 | Token JWT invalide ou révoqué |
| `INVALID_OTP` | 400 | Code OTP incorrect ou expiré |
| `OTP_MAX_ATTEMPTS` | 429 | Trop de tentatives OTP |
| `USER_NOT_FOUND` | 404 | Utilisateur introuvable |
| `PERMISSION_DENIED` | 403 | Action non autorisée |

---

## Flux recommandé côté mobile

```
1. register()         → compte créé
2. login()            → stocker access_token + refresh_token
3. otp/send()         → recevoir code SMS
4. otp/verify()       → telephone_verifie = true
5. [requêtes API]     → Authorization: Bearer <access_token>
6. Si 401 reçu        → refresh() pour obtenir un nouveau token
7. logout()           → révoquer le token, vider le stockage local
```

---

## Sécurité — points clés pour le mobile

- Stocker les tokens dans le **Keychain (iOS)** / **EncryptedSharedPreferences (Android)**
- Ne jamais stocker en clair (AsyncStorage non chiffré)
- Implémenter un **intercepteur HTTP** qui appelle `/refresh` automatiquement sur réception d'un 401
- Si `/refresh` retourne 401 → rediriger vers l'écran de connexion

---

## Infrastructure active

| Service | Hôte | Port |
|---|---|---|
| API GoTaxi | localhost | 8001 |
| PostgreSQL | localhost | 5439 |
| Redis | localhost | 6380 |
| pgAdmin | localhost | 5051 |

> Tests : **21/21 passent** — `pytest tests/integration/test_auth.py`