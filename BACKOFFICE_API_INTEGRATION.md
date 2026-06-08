# GoTaxi — Guide d'intégration API Backoffice

> **Version API :** 2.2.0
> **Date :** 2026-05-05
> **Référence :** GT-ADMIN-API-2026-001
> **Stack frontend :** React 18 · TypeScript · Vite · TanStack Query · Axios · Zod
> **Cible :** Développeur frontend senior — dashboard admin `admin.gotaxi.bj`

Ce document est la **référence unique et complète** pour consommer l'API GoTaxi depuis le dashboard backoffice. Il couvre chaque endpoint, les types TypeScript, les hooks TanStack Query et les patterns de gestion d'erreurs.

---

## Sommaire

1. [Infra & configuration](#1-infra--configuration)
2. [Client HTTP — Axios](#2-client-http--axios)
3. [Authentification admin](#3-authentification-admin)
4. [Module Utilisateurs](#4-module-utilisateurs)
5. [Module Chauffeurs](#5-module-chauffeurs)
6. [Module Voyages](#6-module-voyages)
7. [Module Réservations](#7-module-réservations)
8. [Module Colis](#8-module-colis)
9. [Module Wallet](#9-module-wallet)
10. [Module Transactions](#10-module-transactions)
11. [Module Avis](#11-module-avis)
12. [Module Notifications](#12-module-notifications)
13. [Module Admin — Dashboard](#13-module-admin--dashboard)
14. [Endpoints publics](#14-endpoints-publics)
15. [WebSockets temps réel](#15-websockets-temps-réel)
16. [Types TypeScript complets](#16-types-typescript-complets)
17. [Hooks TanStack Query](#17-hooks-tanstack-query)
18. [Gestion des erreurs](#18-gestion-des-erreurs)
19. [Changelog v2.2 — ce qui a changé](#19-changelog-v22--ce-qui-a-changé)

---

## 1. Infra & configuration

### 1.1 URLs de base

| Environnement | API REST | WebSocket |
|---------------|----------|-----------|
| **Développement** | `http://localhost:8001/api/v1` | `ws://localhost:8001/ws` |
| **Production** | `https://api.gotaxi.bj/api/v1` | `wss://api.gotaxi.bj/ws` |

```bash
# apps/admin/.env
VITE_API_URL=http://localhost:8001/api/v1
VITE_WS_URL=ws://localhost:8001/ws
VITE_MAPBOX_TOKEN=pk.eyJ...
```

### 1.2 Services locaux actifs

| Service | Host | Port |
|---------|------|------|
| API GoTaxi | localhost | **8001** |
| PostgreSQL | localhost | 5439 |
| Redis | localhost | 6380 |
| Swagger UI | localhost | 8001/docs |

> Documentation Swagger interactive : `http://localhost:8001/docs`

### 1.3 Format global

- **Content-Type :** `application/json`
- **Auth :** `Authorization: Bearer <access_token>`
- **Pagination :** `{ items, total, page, size, pages }`
- **Dates :** ISO 8601 UTC — `"2026-05-10T06:00:00Z"`
- **IDs :** UUID v4 — `"a1b2c3d4-..."`

---

## 2. Client HTTP — Axios

### 2.1 Configuration du client

```typescript
// src/lib/api.ts
import axios, { type AxiosInstance } from "axios";
import { useAuthStore } from "@/stores/authStore";

export const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

// Injecter le token sur chaque requête
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Rafraîchir le token automatiquement sur 401
let isRefreshing = false;
let pendingQueue: Array<{ resolve: (v: unknown) => void; reject: (e: unknown) => void }> = [];

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          await useAuthStore.getState().refresh();
          pendingQueue.forEach(({ resolve }) => resolve(null));
        } catch (e) {
          pendingQueue.forEach(({ reject }) => reject(e));
          useAuthStore.getState().logout();
        } finally {
          isRefreshing = false;
          pendingQueue = [];
        }
      } else {
        await new Promise((resolve, reject) => pendingQueue.push({ resolve, reject }));
      }
      return apiClient(original);
    }
    return Promise.reject(error);
  },
);
```

### 2.2 Helper d'extraction de données

```typescript
// Retourne directement r.data pour tous les appels
const get = <T>(url: string, params?: object) =>
  apiClient.get<T>(url, { params }).then((r) => r.data);

const post = <T>(url: string, data?: object) =>
  apiClient.post<T>(url, data).then((r) => r.data);

const patch = <T>(url: string, data?: object) =>
  apiClient.patch<T>(url, data).then((r) => r.data);

const del = <T>(url: string) =>
  apiClient.delete<T>(url).then((r) => r.data);

export { get, post, patch, del };
```

---

## 3. Authentification admin

> L'admin se connecte avec **email + mot de passe**. L'app mobile utilise téléphone + password. Le token admin a un rôle `ADMIN` ou `SUPER_ADMIN` — le front doit vérifier ce rôle après login.

### 3.1 Endpoints Auth

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `POST` | `/auth/login` | — | Connexion (téléphone/mdp) |
| `POST` | `/auth/logout` | Bearer | Déconnexion + révocation token |
| `POST` | `/auth/refresh` | — | Renouveler l'access token |
| `POST` | `/auth/otp/send` | — | Envoyer OTP SMS |
| `POST` | `/auth/otp/verify` | — | Vérifier OTP |
| `POST` | `/auth/password/forgot` | — | Mot de passe oublié |
| `POST` | `/auth/password/reset` | — | Réinitialiser mdp via OTP |
| `POST` | `/auth/password/change` | Bearer | Changer son mdp |

### 3.2 `POST /auth/login`

**Request**
```json
{
  "telephone": "+22997000010",
  "password": "motdepasse123"
}
```

**Response 200**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

> `access_token` : expire dans **30 min** (1800 s).
> `refresh_token` : expire dans **30 jours**.

**Erreurs**
| HTTP | Code | Raison |
|------|------|--------|
| 401 | `INVALID_CREDENTIALS` | Identifiants invalides |
| 403 | `ACCOUNT_SUSPENDED` | Compte suspendu |

### 3.3 `POST /auth/refresh`

**Request**
```json
{ "refresh_token": "eyJhbGci..." }
```

**Response 200** — nouveaux tokens (même structure que `/login`)

**Erreur 401** `TOKEN_INVALID` — rediriger vers `/login`

### 3.4 `POST /auth/logout`

`Authorization: Bearer <access_token>` requis.

**Response 200** `{ "message": "Déconnexion réussie" }`

### 3.5 `POST /auth/password/change`

**Request**
```json
{
  "current_password": "motdepasse123",
  "new_password": "nouveaumdp2024"
}
```

**Response 200** `{ "message": "Mot de passe modifié" }`

### 3.6 Auth Store Zustand

```typescript
// src/stores/authStore.ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { apiClient } from "@/lib/api";
import type { AdminUser } from "@/types/domain";

interface AuthState {
  user: AdminUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (telephone: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,

      login: async (telephone, password) => {
        const { data } = await apiClient.post<{ access_token: string; refresh_token: string }>(
          "/auth/login",
          { telephone, password },
        );
        // Récupérer le profil pour vérifier le rôle admin
        const { data: user } = await apiClient.get<AdminUser>("/users/me", {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });
        if (!["ADMIN", "SUPER_ADMIN"].includes(user.role)) {
          throw new Error("Accès refusé : compte non administrateur");
        }
        localStorage.setItem("gotaxi_refresh_token", data.refresh_token);
        set({ user, accessToken: data.access_token, isAuthenticated: true });
      },

      logout: () => {
        const token = get().accessToken;
        if (token) apiClient.post("/auth/logout").catch(() => {});
        localStorage.removeItem("gotaxi_refresh_token");
        set({ user: null, accessToken: null, isAuthenticated: false });
        window.location.href = "/login";
      },

      refresh: async () => {
        const refreshToken = localStorage.getItem("gotaxi_refresh_token");
        if (!refreshToken) throw new Error("No refresh token");
        const { data } = await apiClient.post<{ access_token: string; refresh_token: string }>(
          "/auth/refresh",
          { refresh_token: refreshToken },
        );
        localStorage.setItem("gotaxi_refresh_token", data.refresh_token);
        set({ accessToken: data.access_token });
      },
    }),
    {
      name: "gotaxi-admin-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ user: s.user, accessToken: s.accessToken, isAuthenticated: s.isAuthenticated }),
    },
  ),
);
```

---

## 4. Module Utilisateurs

### 4.1 Endpoints

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `GET` | `/users/me` | Bearer | Mon profil |
| `PATCH` | `/users/me` | Bearer | Modifier mon profil |
| `DELETE` | `/users/me` | Bearer | Supprimer mon compte |
| `POST` | `/users/me/photo` | Bearer | Upload photo de profil |
| `POST` | `/users/me/fcm-token?token=<t>` | Bearer | Enregistrer token push |
| `GET` | `/users/me/avis` | Bearer | Mes avis reçus |
| `GET` | `/users/{user_id}` | Bearer | Profil public d'un utilisateur |

### 4.2 `GET /users/me` — Profil complet

**Response 200**
```json
{
  "id": "uuid",
  "telephone": "+22997000010",
  "email": "admin@gotaxi.bj",
  "nom": "Adjovi",
  "prenom": "Serge",
  "photo_url": "https://bucket.s3.amazonaws.com/profiles/uuid.jpg",
  "role": "ADMIN",
  "statut": "ACTIF",
  "telephone_verifie": true,
  "note_moyenne": 0.0,
  "nombre_avis": 0,
  "langue": "fr",
  "created_at": "2026-01-15T08:00:00Z"
}
```

| Champ | Valeurs |
|-------|---------|
| `role` | `CLIENT` · `CHAUFFEUR` · `ADMIN` · `SUPER_ADMIN` |
| `statut` | `ACTIF` · `SUSPENDU` · `EN_ATTENTE_KYC` · `SUPPRIME` |

### 4.3 `PATCH /users/me` — Modifier profil

**Request** (tous les champs optionnels)
```json
{
  "nom": "Nouveau Nom",
  "prenom": "Nouveau Prénom",
  "email": "nouveau@gotaxi.bj",
  "langue": "fr"
}
```

**Response 200** — profil mis à jour (même structure)

### 4.4 `POST /users/me/photo` — Upload photo

`Content-Type: multipart/form-data`

| Champ | Type | Contrainte |
|-------|------|------------|
| `file` | File | JPEG · PNG · WebP — max 5 Mo |

**Response 200** — profil avec `photo_url` mis à jour

### 4.5 `GET /users/{user_id}` — Profil public

**Response 200**
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

### 4.6 Client API

```typescript
// src/lib/api/users.ts
import { get, patch, post, del } from "@/lib/api";
import type { UserRead, UserUpdate, AvisRead } from "@/types/domain";

export const usersApi = {
  me: () => get<UserRead>("/users/me"),
  updateMe: (data: UserUpdate) => patch<UserRead>("/users/me", data),
  deleteMe: () => del<{ message: string }>("/users/me"),
  uploadPhoto: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post<UserRead>("/users/me/photo", form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data);
  },
  registerFcmToken: (token: string) =>
    post<{ message: string }>(`/users/me/fcm-token?token=${encodeURIComponent(token)}`),
  myAvis: () => get<AvisRead[]>("/users/me/avis"),
  publicProfile: (userId: string) => get<UserRead>(`/users/${userId}`),
};
```

---

## 5. Module Chauffeurs

### 5.1 Endpoints

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `GET` | `/chauffeurs/me` | Bearer (CHAUFFEUR) | Mon profil chauffeur |
| `PATCH` | `/chauffeurs/me` | Bearer (CHAUFFEUR) | Modifier profil chauffeur |
| `POST` | `/chauffeurs/me/documents` | Bearer (CHAUFFEUR) | Upload docs KYC |
| `POST` | `/chauffeurs/me/online` | Bearer (CHAUFFEUR) | Passer en ligne |
| `POST` | `/chauffeurs/me/offline` | Bearer (CHAUFFEUR) | Passer hors ligne |
| `POST` | `/chauffeurs/me/position` | Bearer (CHAUFFEUR) | Mettre à jour position GPS |
| `GET` | `/chauffeurs/me/stats` | Bearer (CHAUFFEUR) | Statistiques |
| `GET` | `/chauffeurs/me/revenus` | Bearer (CHAUFFEUR) | Revenus |
| `GET` | `/chauffeurs/me/vehicules` | Bearer (CHAUFFEUR) | Mes véhicules |
| `POST` | `/chauffeurs/me/vehicules` | Bearer (CHAUFFEUR) | Ajouter un véhicule |
| `PATCH` | `/chauffeurs/me/vehicules/{id}` | Bearer (CHAUFFEUR) | Modifier un véhicule |
| `DELETE` | `/chauffeurs/me/vehicules/{id}` | Bearer (CHAUFFEUR) | Supprimer un véhicule |
| `GET` | `/chauffeurs/{id}` | Bearer | Profil public chauffeur |
| `GET` | `/chauffeurs/{id}/voyages` | Bearer | Voyages d'un chauffeur |

### 5.2 `GET /chauffeurs/me` — Profil chauffeur complet

**Response 200**
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

### 5.3 `POST /chauffeurs/me/documents` — Upload KYC

`Content-Type: multipart/form-data` — envoyer au moins un fichier.

| Champ | Description |
|-------|-------------|
| `cin` | Photo CIN recto (JPEG/PNG/WebP · max 5 Mo) |
| `permis` | Photo permis de conduire |
| `casier_judiciaire` | Extrait casier judiciaire |

**Response 200** — profil chauffeur avec URLs de documents

### 5.4 `POST /chauffeurs/me/position` — GPS

**Request**
```json
{
  "lat": 6.3703,
  "lng": 2.3912,
  "vitesse": 68.5,
  "heading": 45.0
}
```

**Response 204** (pas de corps)

> Si un voyage `EN_COURS` est actif, la position est broadcastée en temps réel via WebSocket aux passagers.

### 5.5 `GET /chauffeurs/me/stats` & `/revenus`

**Stats**
```json
{
  "nombre_trajets": 142,
  "revenus_total": 710000,
  "note_moyenne": 4.7,
  "nombre_avis": 89,
  "en_ligne": false
}
```

**Revenus**
```json
{
  "aujourd_hui": 15000,
  "semaine": 87000,
  "mois": 320000,
  "total": 710000
}
```

### 5.6 Gestion des véhicules

#### `POST /chauffeurs/me/vehicules` — Ajouter

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

| Champ | Contrainte |
|-------|-----------|
| `annee` | 2000–2030 |
| `type_vehicule` | `BERLINE` · `SUV` · `MINIBUS` · `BUS` · `MOTO` |
| `nombre_places` | 1–20 |

**Response 201** — véhicule créé | **409** si immatriculation déjà utilisée

#### `PATCH /chauffeurs/me/vehicules/{id}` — Modifier

```json
{ "couleur": "Rouge", "nombre_places": 5, "climatise": false }
```

#### `DELETE /chauffeurs/me/vehicules/{id}` — Supprimer (soft delete)

**Response 200** `{ "message": "Véhicule supprimé" }`

---

## 6. Module Voyages

### 6.1 Endpoints

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `POST` | `/voyages` | Bearer (CHAUFFEUR) | Publier un trajet |
| `GET` | `/voyages/search` | Bearer | Recherche passagers |
| `GET` | `/voyages/colis-search` | Bearer | Recherche pour colis ⭐ |
| `GET` | `/voyages/popular` | **Public** | Trajets populaires (accueil) |
| `GET` | `/voyages/me` | Bearer (CHAUFFEUR) | Mes voyages |
| `GET` | `/voyages/{id}` | Bearer | Détail d'un voyage |
| `PATCH` | `/voyages/{id}` | Bearer (CHAUFFEUR, owner) | Modifier (avant départ) |
| `POST` | `/voyages/{id}/start` | Bearer (CHAUFFEUR, owner) | Démarrer |
| `POST` | `/voyages/{id}/end` | Bearer (CHAUFFEUR, owner) | Terminer |
| `POST` | `/voyages/{id}/cancel` | Bearer (CHAUFFEUR, owner) | Annuler |
| `GET` | `/voyages/{id}/passagers` | Bearer (CHAUFFEUR, owner) | Passagers confirmés |
| `GET` | `/voyages/{id}/reservations` | Bearer (CHAUFFEUR, owner) | Toutes les réservations ⭐ |

### 6.2 Statuts d'un voyage

```
PUBLIE ──┬── (places saturées auto) ──► COMPLET
         │                                  │
         ├── /start (PUBLIE ou COMPLET) ──► EN_COURS ──► /end ──► TERMINE
         │
         └── /cancel (PUBLIE ou COMPLET) ──► ANNULE
```

### 6.3 `POST /voyages` — Publier un trajet

**Prérequis :** KYC validé + être en ligne + avoir un véhicule actif.

**Request**
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
  "vehicule_id": "uuid-vehicule",
  "accepte_colis": true,
  "climatise": true,
  "non_fumeur": true
}
```

| Champ | Type | Requis | Contrainte |
|-------|------|:------:|-----------|
| `prix_par_place` | int | ✅ | 500–100 000 FCFA |
| `nombre_places_total` | int | ✅ | 1–8 |
| `date_depart` | datetime | ✅ | ISO 8601 UTC |
| `vehicule_id` | uuid | ✅ | Doit appartenir au chauffeur |

**Response 201** → `VoyageRead`

**Erreurs**
| HTTP | Raison |
|------|--------|
| 403 | KYC non validé ou chauffeur hors ligne |
| 404 | Véhicule introuvable ou inactif |

### 6.4 `GET /voyages/search` — Recherche passagers

| Paramètre | Type | Requis | Défaut | Description |
|-----------|------|:------:|--------|-------------|
| `ville_depart` | string | ✅ | — | Ex: `Cotonou` |
| `ville_arrivee` | string | ✅ | — | Ex: `Parakou` |
| `date_depart` | date | ✅ | — | `YYYY-MM-DD` |
| `nombre_places` | int | — | `1` | Places min disponibles |
| `accepte_colis` | bool | — | — | Filtrer si accepte colis |
| `climatise` | bool | — | — | Filtrer si climatisé |
| `prix_max` | int | — | — | Prix max/place (FCFA) |
| `sort_by` | string | — | `depart_asc` | `prix_asc` · `prix_desc` · `depart_asc` · `depart_desc` |
| `page` | int | — | `1` | — |
| `size` | int | — | `20` | Max 100 |

> **Retourne uniquement les voyages `PUBLIE`.** Pour les colis, utiliser `/voyages/colis-search`.

**Response 200**
```json
{
  "items": [ /* VoyageRead[] */ ],
  "total": 12,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

### 6.5 `GET /voyages/colis-search` — Recherche pour colis ⭐

Même structure de paramètres que `/search` **sans** `nombre_places`, `climatise`, `prix_max`.

| Paramètre | Type | Requis |
|-----------|------|:------:|
| `ville_depart` | string | ✅ |
| `ville_arrivee` | string | ✅ |
| `date_depart` | date | ✅ |
| `sort_by` · `page` · `size` | — | — |

> Retourne les voyages en statut **`PUBLIE` + `COMPLET` + `EN_COURS`** avec `accepte_colis = true`.
>
> **Règle :** utiliser **exclusivement** cet endpoint dans l'écran "Envoyer un colis". Ne jamais utiliser `/voyages/search` pour ce cas d'usage.

### 6.6 `GET /voyages/{id}` — Détail

**Règles de visibilité client :**
- `PUBLIE` ou `COMPLET` → toujours accessible
- `EN_COURS` ou `TERMINE` → uniquement si le client a une réservation active (`EN_ATTENTE`, `CONFIRMEE` ou `TERMINEE`)

### 6.7 Schéma `VoyageRead`

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

### 6.8 `POST /voyages/{id}/start|end|cancel`

| Action | Statut requis | Nouveau statut | Effet sur réservations |
|--------|--------------|----------------|----------------------|
| `start` | `PUBLIE` ou `COMPLET` | `EN_COURS` | Aucun |
| `end` | `EN_COURS` | `TERMINE` | `CONFIRMEE` → `TERMINEE` |
| `cancel` | `PUBLIE` ou `COMPLET` | `ANNULE` | `EN_ATTENTE` + `CONFIRMEE` → `ANNULEE` |

**Response 200** `{ "message": "Voyage démarré|terminé|annulé" }`

### 6.9 Client API

```typescript
// src/lib/api/voyages.ts
import { get, post, patch } from "@/lib/api";
import type { VoyageRead, VoyageCreate, VoyageUpdate, PaginatedResponse } from "@/types/domain";

export const voyagesApi = {
  create: (data: VoyageCreate) => post<VoyageRead>("/voyages", data),
  search: (params: VoyageSearchParams) => get<PaginatedResponse<VoyageRead>>("/voyages/search", params),
  colisSearch: (params: ColisSearchParams) => get<PaginatedResponse<VoyageRead>>("/voyages/colis-search", params),
  popular: () => get<VoyageRead[]>("/voyages/popular"),
  me: () => get<VoyageRead[]>("/voyages/me"),
  detail: (id: string) => get<VoyageRead>(`/voyages/${id}`),
  update: (id: string, data: VoyageUpdate) => patch<VoyageRead>(`/voyages/${id}`, data),
  start: (id: string) => post<{ message: string }>(`/voyages/${id}/start`),
  end: (id: string) => post<{ message: string }>(`/voyages/${id}/end`),
  cancel: (id: string) => post<{ message: string }>(`/voyages/${id}/cancel`),
  passagers: (id: string) => get<ReservationRead[]>(`/voyages/${id}/passagers`),
  reservations: (id: string, statut?: ReservationStatut) =>
    get<ReservationRead[]>(`/voyages/${id}/reservations`, statut ? { statut } : undefined),
};
```

---

## 7. Module Réservations

### 7.1 Endpoints

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `POST` | `/reservations` | Bearer | Créer une réservation |
| `GET` | `/reservations/me` | Bearer | Mes réservations (client) |
| `GET` | `/reservations/me/incoming` | Bearer (CHAUFFEUR) | Demandes EN_ATTENTE |
| `GET` | `/reservations/{id}` | Bearer | Détail d'une réservation |
| `POST` | `/reservations/{id}/accept` | Bearer (CHAUFFEUR, owner) | Accepter |
| `POST` | `/reservations/{id}/reject` | Bearer (CHAUFFEUR, owner) | Refuser |
| `POST` | `/reservations/{id}/cancel` | Bearer (client ou chauffeur) | Annuler |

### 7.2 Schéma `ReservationRead` (v2.1)

> **Important :** les champs `voyage` et `client` sont **embedded** dans la réponse. Ne plus faire d'appels séparés.

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

**Présence des champs embedded par endpoint :**

| Endpoint | `voyage` | `client` |
|----------|:--------:|:--------:|
| `GET /reservations/me` | ✅ renseigné | `null` |
| `GET /reservations/me/incoming` | ✅ renseigné | ✅ renseigné |
| `GET /reservations/{id}` | ✅ renseigné | ✅ renseigné |
| `POST /reservations` (création) | ✅ renseigné | `null` |
| `POST /reservations/{id}/accept` | `null` | ✅ renseigné |
| `POST /reservations/{id}/reject` | `null` | ✅ renseigné |
| `POST /reservations/{id}/cancel` | ✅ renseigné | optionnel |

### 7.3 Statuts d'une réservation

```
EN_ATTENTE ──┬── accept (chauffeur) ──► CONFIRMEE ──── voyage /end ──► TERMINEE
             ├── reject (chauffeur) ──► REFUSEE             │
             └── cancel             ──► ANNULEE         /cancel ──────► ANNULEE
```

`REFUSEE`, `ANNULEE`, `TERMINEE` sont des **statuts terminaux** — irréversibles via API.

### 7.4 `POST /reservations` — Créer

**Request**
```json
{
  "voyage_id": "uuid-du-voyage",
  "nombre_places": 2
}
```

**Response 201** → `ReservationRead` avec `voyage` embedded, `client: null`

> `prix_total` = `prix_par_place × nombre_places` — calculé côté serveur.
> `code_confirmation` — code à 6 caractères à présenter au chauffeur.

**Erreurs**
| HTTP | Raison |
|------|--------|
| 403 | Chauffeur réservant son propre voyage |
| 404 | Voyage introuvable |
| 409 | Plus de places ou voyage non PUBLIE |

### 7.5 `POST /reservations/{id}/accept|reject|cancel`

> **v2.1 :** Ces trois endpoints retournent **`ReservationRead`** (plus `{ message }` seul).
> Lire `response.statut` et `response.client` — ne plus lire `response.message`.

**Response 200** → `ReservationRead` complet

### 7.6 Vue chauffeur — endpoint recommandé par écran

| Écran | Endpoint |
|-------|----------|
| Badge / compteur demandes | `GET /reservations/me/incoming` |
| Page détail voyage — onglet "Demandes" | `GET /voyages/{id}/reservations?statut=EN_ATTENTE` |
| Page détail voyage — onglet "Passagers" | `GET /voyages/{id}/reservations?statut=CONFIRMEE` |
| Historique complet d'un voyage | `GET /voyages/{id}/reservations` |

### 7.7 Client API

```typescript
// src/lib/api/reservations.ts
import { get, post } from "@/lib/api";
import type { ReservationRead, ReservationCreate } from "@/types/domain";

export const reservationsApi = {
  create: (data: ReservationCreate) => post<ReservationRead>("/reservations", data),
  me: () => get<ReservationRead[]>("/reservations/me"),
  incoming: () => get<ReservationRead[]>("/reservations/me/incoming"),
  detail: (id: string) => get<ReservationRead>(`/reservations/${id}`),
  accept: (id: string) => post<ReservationRead>(`/reservations/${id}/accept`),
  reject: (id: string) => post<ReservationRead>(`/reservations/${id}/reject`),
  cancel: (id: string) => post<ReservationRead>(`/reservations/${id}/cancel`),
};
```

---

## 8. Module Colis

### 8.1 Endpoints

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `POST` | `/colis` | Bearer | Envoyer un colis |
| `GET` | `/colis/me` | Bearer | Mes colis (expéditeur) |
| `GET` | `/colis/voyage/{voyage_id}` | Bearer (CHAUFFEUR, owner) | Colis d'un voyage |
| `GET` | `/colis/{id}` | Bearer | Détail d'un colis |
| `POST` | `/colis/{id}/confirmer` | Bearer (CHAUFFEUR) | Accepter le colis |
| `POST` | `/colis/{id}/en_transit` | Bearer (CHAUFFEUR) | Marquer en route |
| `POST` | `/colis/{id}/livrer` | Bearer (CHAUFFEUR) | Marquer livré |
| `POST` | `/colis/{id}/annuler` | Bearer | Annuler |

### 8.2 `POST /colis` — Envoyer un colis (v2.2)

**Request**
```json
{
  "voyage_id": "uuid-du-voyage",
  "description": "Ordinateur portable pour mon frère",
  "categorie": "ELECTRONIQUE",
  "poids_kg": 2.0,
  "fragile": true,
  "destinataire_nom": "Kofi Mensah",
  "destinataire_telephone": "+22967890123",
  "modalite_paiement": "A_LA_LIVRAISON"
}
```

| Champ | Type | Requis | Valeurs |
|-------|------|:------:|---------|
| `voyage_id` | uuid | ✅ | Voyage `PUBLIE` · `COMPLET` · `EN_COURS` |
| `categorie` | enum | ✅ | `DOCUMENTS` · `VETEMENTS` · `ELECTRONIQUE` · `ALIMENTAIRE` · `FRAGILE` · `AUTRE` |
| `poids_kg` | float | — | — |
| `fragile` | bool | ✅ | — |
| `modalite_paiement` | enum | — | `A_LA_CONFIRMATION` · `A_LA_LIVRAISON` (défaut) |

> **Ne jamais afficher un champ "Prix" à l'utilisateur.** Le prix est calculé automatiquement par le serveur.

### 8.3 Logique de tarification (calculée côté serveur)

```
prix = max(500, arrondi(
    distance_km × 3 FCFA × coeff_categorie
    + poids_kg  × 100 FCFA
    + supplément fragile (+300 FCFA si fragile = true)
))
```

| Catégorie | Coefficient |
|-----------|:-----------:|
| `DOCUMENTS` | × 0.8 |
| `VETEMENTS` | × 1.0 |
| `ALIMENTAIRE` | × 1.1 |
| `ELECTRONIQUE` | × 1.5 |
| `FRAGILE` | × 1.5 |
| `AUTRE` | × 1.0 |

**Prix plancher : 500 FCFA**

### 8.4 Schéma `ColisRead` (v2.2)

```json
{
  "id": "uuid",
  "voyage_id": "uuid",
  "expediteur_id": "uuid",
  "ville_depart": "Cotonou",
  "ville_arrivee": "Parakou",
  "description": "Ordinateur portable pour mon frère",
  "categorie": "ELECTRONIQUE",
  "poids_kg": 2.0,
  "fragile": true,
  "destinataire_nom": "Kofi Mensah",
  "destinataire_telephone": "+22967890123",
  "prix": 2390,
  "modalite_paiement": "A_LA_LIVRAISON",
  "statut": "EN_ATTENTE",
  "code_suivi": "GTX-X7K2M4",
  "photo_url": null,
  "voyage": { /* VoyageRead embedded */ },
  "created_at": "2026-05-04T10:00:00Z",
  "updated_at": "2026-05-04T10:00:00Z"
}
```

> `prix` est **toujours renseigné** (plus jamais `null`) depuis la v2.2.

### 8.5 Statuts d'un colis

```
EN_ATTENTE ──► (chauffeur /confirmer) ──► CONFIRME
                                              │
                                         /en_transit (voyage EN_COURS requis)
                                              │
                                           EN_TRANSIT ──► /livrer ──► LIVRE
                                              │
                                          /annuler ──► ANNULE
```

| Transition | Endpoint | Prérequis |
|-----------|----------|-----------|
| `EN_ATTENTE` → `CONFIRME` | `POST /colis/{id}/confirmer` | Chauffeur du voyage |
| `CONFIRME` → `EN_TRANSIT` | `POST /colis/{id}/en_transit` | Voyage doit être `EN_COURS` |
| `EN_TRANSIT` → `LIVRE` | `POST /colis/{id}/livrer` | — |
| `EN_ATTENTE` → `ANNULE` | `POST /colis/{id}/annuler` | Chauffeur ou client |

### 8.6 Affichage selon `modalite_paiement`

```typescript
function getColisPaymentMessage(colis: Colis): string {
  const { statut, modalite_paiement, prix } = colis;
  switch (statut) {
    case "EN_ATTENTE":
      return `En attente du chauffeur — prix estimé : ${prix.toLocaleString()} FCFA`;
    case "CONFIRME":
      return modalite_paiement === "A_LA_CONFIRMATION"
        ? `Paiement requis : ${prix.toLocaleString()} FCFA`
        : `Accepté — paiement à la livraison`;
    case "EN_TRANSIT":
      return modalite_paiement === "A_LA_LIVRAISON"
        ? `En route — préparez ${prix.toLocaleString()} FCFA`
        : `En route`;
    case "LIVRE":
      return modalite_paiement === "A_LA_LIVRAISON"
        ? `Livré — paiement de ${prix.toLocaleString()} FCFA à effectuer`
        : `Livré ✓`;
    case "ANNULE":
      return "Colis annulé";
    default:
      return statut;
  }
}
```

### 8.7 Client API

```typescript
// src/lib/api/colis.ts
import { get, post } from "@/lib/api";
import type { ColisRead, ColisCreate } from "@/types/domain";

export const colisApi = {
  create: (data: ColisCreate) => post<ColisRead>("/colis", data),
  me: () => get<ColisRead[]>("/colis/me"),
  byVoyage: (voyageId: string) => get<ColisRead[]>(`/colis/voyage/${voyageId}`),
  detail: (id: string) => get<ColisRead>(`/colis/${id}`),
  confirmer: (id: string) => post<ColisRead>(`/colis/${id}/confirmer`),
  enTransit: (id: string) => post<ColisRead>(`/colis/${id}/en_transit`),
  livrer: (id: string) => post<ColisRead>(`/colis/${id}/livrer`),
  annuler: (id: string) => post<ColisRead>(`/colis/${id}/annuler`),
};
```

---

## 9. Module Wallet

### 9.1 Endpoints

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `GET` | `/wallet/me` | Bearer | Solde du wallet |
| `GET` | `/wallet/me/activity` | Bearer | Historique transactions |
| `POST` | `/wallet/me/recharge/initiate` | Bearer | Initier une recharge MoMo |
| `POST` | `/wallet/me/recharge/confirm` | Bearer | Confirmer la recharge |
| `POST` | `/wallet/me/withdraw` | Bearer | Retrait vers MoMo |
| `POST` | `/wallet/me/transfer` | Bearer | Transfert wallet → wallet |

### 9.2 `GET /wallet/me` — Solde

**Response 200**
```json
{
  "id": "uuid",
  "solde": 45000,
  "devise": "XOF",
  "actif": true
}
```

### 9.3 `GET /wallet/me/activity` — Historique

**Query params :** `page` (défaut 1), `size` (défaut 20, max 100)

**Response 200** → `PaginatedResponse<TransactionRead>`

### 9.4 `POST /wallet/me/recharge/initiate` — Initier recharge

**Request**
```json
{
  "montant": 5000,
  "operateur": "MTN",
  "telephone": "+22997000010"
}
```

| Champ | Contrainte |
|-------|-----------|
| `montant` | 500–1 000 000 FCFA |
| `operateur` | `MTN` · `MOOV` · `ORANGE` · `WALLET` |

**Response 200** `{ "message": "Recharge initiée via MTN. Confirmez le paiement USSD." }`

### 9.5 `POST /wallet/me/recharge/confirm?transaction_id=<uuid>`

> À appeler après que l'utilisateur a confirmé le paiement USSD.

**Response 200** → `WalletRead` avec solde mis à jour

**Erreur 400** si transaction déjà traitée, **404** si transaction introuvable.

### 9.6 `POST /wallet/me/withdraw` — Retrait

**Request**
```json
{
  "montant": 10000,
  "telephone": "+22997000010",
  "operateur": "MTN"
}
```

**Erreur 402** si solde insuffisant.

### 9.7 `POST /wallet/me/transfer` — Transfert interne

**Request**
```json
{
  "destinataire_telephone": "+22967000020",
  "montant": 3000
}
```

**Response 200** `{ "message": "Transfert de 3000 XOF effectué" }`

---

## 10. Module Transactions

### 10.1 Endpoints

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `GET` | `/transactions/me` | Bearer | Mes transactions |
| `GET` | `/transactions/{id}` | Bearer | Détail d'une transaction |

### 10.2 `GET /transactions/me`

**Query params :** `page` (défaut 1), `size` (défaut 20, max 100)

**Response 200** → `PaginatedResponse<TransactionRead>`

### 10.3 Schéma `TransactionRead`

```json
{
  "id": "uuid",
  "type": "RECHARGE",
  "statut": "REUSSI",
  "operateur": "MTN",
  "montant": 5000,
  "created_at": "2026-05-04T12:00:00Z"
}
```

| Champ | Valeurs |
|-------|---------|
| `type` | `RECHARGE` · `REVERSEMENT` · `PAIEMENT` · `REMBOURSEMENT` |
| `statut` | `EN_ATTENTE` · `REUSSI` · `ECHOUE` · `ANNULE` |
| `operateur` | `MTN` · `MOOV` · `ORANGE` · `WALLET` |

---

## 11. Module Avis

### 11.1 Endpoints

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `POST` | `/avis` | Bearer | Créer un avis |
| `GET` | `/avis/chauffeur/{id}` | Public | Avis sur un chauffeur |
| `GET` | `/avis/me/recus` | Bearer | Mes avis reçus |
| `POST` | `/avis/{id}/signaler` | Bearer | Signaler un avis |

### 11.2 `POST /avis` — Créer un avis

**Request**
```json
{
  "cible_id": "uuid-de-la-cible",
  "voyage_id": "uuid-du-voyage",
  "note": 5,
  "commentaire": "Excellent chauffeur, très ponctuel",
  "tags": ["ponctuel", "propre"]
}
```

| Champ | Contrainte |
|-------|-----------|
| `note` | 1–5 |

**Response 201** → `AvisRead`

### 11.3 `GET /avis/chauffeur/{id}` — Avis sur un chauffeur

**Query params :** `page`, `size`

**Response 200** → `PaginatedResponse<AvisRead>`

### 11.4 Schéma `AvisRead`

```json
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
```

---

## 12. Module Notifications

### 12.1 Endpoints

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `GET` | `/notifications/me` | Bearer | Mes notifications |
| `GET` | `/notifications/me/unread-count` | Bearer | Compteur non lues |
| `POST` | `/notifications/me/read-all` | Bearer | Tout marquer comme lu |
| `POST` | `/notifications/{id}/read` | Bearer | Marquer une notif comme lue |
| `DELETE` | `/notifications/{id}` | Bearer | Supprimer une notification |

### 12.2 `GET /notifications/me`

**Query params :** `page`, `size`

**Response 200** → `PaginatedResponse<NotificationRead>`

### 12.3 `GET /notifications/me/unread-count`

**Response 200** `{ "count": 3 }`

### 12.4 Schéma `NotificationRead`

```json
{
  "id": "uuid",
  "type": "RESERVATION_ACCEPTED",
  "titre": "Réservation confirmée",
  "corps": "Votre réservation Cotonou → Parakou a été acceptée.",
  "lue": false,
  "data": { "reservation_id": "uuid", "voyage_id": "uuid" },
  "created_at": "2026-05-04T09:30:00Z"
}
```

| `type` | Déclencheur |
|--------|-------------|
| `RESERVATION_ACCEPTED` | Chauffeur accepte une demande |
| `RESERVATION_REJECTED` | Chauffeur refuse une demande |
| `RESERVATION_CANCELLED` | Annulation par l'autre partie |
| `VOYAGE_STARTED` | Voyage démarré |
| `VOYAGE_ENDED` | Voyage terminé |
| `COLIS_CONFIRMED` | Colis accepté |
| `COLIS_DELIVERED` | Colis livré |
| `KYC_VALIDATED` | KYC validé par admin |
| `NEW_RESERVATION` | Nouvelle demande (chauffeur) |

---

## 13. Module Admin — Dashboard

> Tous les endpoints `/admin/*` nécessitent le rôle `ADMIN` ou `SUPER_ADMIN`.

### 13.1 Endpoints admin

| Méthode | Endpoint | Auth | Description |
|---------|----------|:----:|-------------|
| `GET` | `/admin/dashboard/overview` | ADMIN | KPIs globaux |
| `GET` | `/admin/users` | ADMIN | Liste des utilisateurs |
| `POST` | `/admin/users/{id}/suspend` | ADMIN | Suspendre un utilisateur |
| `GET` | `/admin/colis/pending` | ADMIN | Colis en attente |
| `POST` | `/admin/colis/{id}/validate` | ADMIN | Valider un colis |

### 13.2 `GET /admin/dashboard/overview`

**Response 200**
```json
{
  "total_utilisateurs": 3240,
  "total_voyages": 8510,
  "total_colis": 1204
}
```

> Pour les KPIs avancés (revenus, courses actives, chauffeurs online), étendre côté backend ou calculer côté front depuis les endpoints existants.

### 13.3 `GET /admin/users`

**Response 200** → `UserRead[]` (max 100 résultats)

> Pour la pagination et les filtres avancés (statut, rôle, recherche), utiliser les query params standard ou attendre l'implémentation de la pagination côté backend.

### 13.4 `POST /admin/users/{id}/suspend`

**Response 200** `{ "message": "Utilisateur suspendu" }`

### 13.5 `GET /admin/colis/pending`

**Response 200** → `ColisRead[]` (statut `EN_ATTENTE`)

### 13.6 `POST /admin/colis/{id}/validate`

**Response 200** `{ "message": "Colis validé" }`

### 13.7 Client API admin

```typescript
// src/lib/api/admin.ts
import { get, post } from "@/lib/api";
import type { UserRead, ColisRead } from "@/types/domain";

export const adminApi = {
  overview: () => get<AdminOverview>("/admin/dashboard/overview"),
  users: () => get<UserRead[]>("/admin/users"),
  suspendUser: (userId: string) => post<{ message: string }>(`/admin/users/${userId}/suspend`),
  pendingColis: () => get<ColisRead[]>("/admin/colis/pending"),
  validateColis: (colisId: string) => post<{ message: string }>(`/admin/colis/${colisId}/validate`),
};
```

---

## 14. Endpoints publics

Ces endpoints ne requièrent **aucun token**.

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/public/health` | Santé de l'API |
| `GET` | `/public/health/db` | Santé de la base de données |
| `GET` | `/public/villes` | Liste des villes desservies |
| `GET` | `/public/stats` | Statistiques publiques |
| `GET` | `/voyages/popular` | 10 prochains voyages PUBLIE |

### `GET /public/villes`

**Response 200**
```json
{
  "villes": [
    "Cotonou", "Porto-Novo", "Parakou", "Abomey-Calavi",
    "Bohicon", "Natitingou", "Kandi", "Lokossa",
    "Ouidah", "Abomey", "Djougou"
  ]
}
```

### `GET /public/stats`

**Response 200**
```json
{
  "total_voyages": 8510,
  "villes_desservies": 11
}
```

---

## 15. WebSockets temps réel

### 15.1 Canaux disponibles

| Canal | URL | Auth | Description |
|-------|-----|:----:|-------------|
| Tracking GPS | `/ws/tracking/voyage/{voyage_id}` | token query | Position chauffeur en direct |
| Notifications | `/ws/notifications` | token query | Notifications push |
| Activité admin | `/ws/admin/activity` | token query | Feed activité backoffice |

**Authentification WebSocket :** passer le token en query param.
```
ws://localhost:8001/ws/tracking/voyage/{id}?token=<access_token>
```

### 15.2 Messages reçus — Tracking GPS

```json
{
  "type": "position_update",
  "voyage_id": "uuid",
  "lat": 7.1234,
  "lng": 2.4321,
  "vitesse": 85.0,
  "heading": 30.0,
  "timestamp": "2026-05-10T09:15:00Z"
}
```

### 15.3 Hook `useWebSocket`

```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from "react";
import { useAuthStore } from "@/stores/authStore";

interface Options {
  onMessage?: (msg: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectDelay?: number;
  enabled?: boolean;
}

export function useWebSocket(channel: string, options: Options = {}) {
  const { onMessage, onConnect, onDisconnect, reconnectDelay = 3000, enabled = true } = options;
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!enabled) return;
    const token = useAuthStore.getState().accessToken;
    const url = `${import.meta.env.VITE_WS_URL}/${channel}?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => { setIsConnected(true); onConnect?.(); };
    ws.onclose = () => {
      setIsConnected(false);
      onDisconnect?.();
      timerRef.current = setTimeout(connect, reconnectDelay);
    };
    ws.onmessage = (e) => {
      try { onMessage?.(JSON.parse(e.data)); } catch {}
    };
    ws.onerror = () => ws.close();
  }, [channel, enabled, reconnectDelay]);

  useEffect(() => {
    connect();
    return () => {
      timerRef.current && clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: unknown) => {
    wsRef.current?.send(JSON.stringify(data));
  }, []);

  return { isConnected, send };
}
```

### 15.4 Utilisation pour la carte flotte

```typescript
// src/hooks/useFleet.ts
import { useState, useCallback } from "react";
import { useWebSocket } from "./useWebSocket";

interface DriverPosition {
  voyage_id: string;
  lat: number;
  lng: number;
  vitesse: number;
  heading: number;
  timestamp: string;
}

export function useVoyageTracking(voyageId: string | null) {
  const [position, setPosition] = useState<DriverPosition | null>(null);

  useWebSocket(`tracking/voyage/${voyageId}`, {
    enabled: !!voyageId,
    onMessage: (msg) => {
      const m = msg as { type: string } & DriverPosition;
      if (m.type === "position_update") setPosition(m);
    },
  });

  return { position };
}
```

---

## 16. Types TypeScript complets

```typescript
// src/types/domain.ts

// ─── Enums ─────────────────────────────────────────────────────────────────

export type UserRole = "CLIENT" | "CHAUFFEUR" | "ADMIN" | "SUPER_ADMIN";
export type UserStatut = "ACTIF" | "SUSPENDU" | "EN_ATTENTE_KYC" | "SUPPRIME";

export type VoyageStatut = "PUBLIE" | "COMPLET" | "EN_COURS" | "TERMINE" | "ANNULE";

export type ReservationStatut =
  | "EN_ATTENTE"
  | "CONFIRMEE"
  | "REFUSEE"
  | "ANNULEE"
  | "TERMINEE";

export type ColisStatut = "EN_ATTENTE" | "CONFIRME" | "EN_TRANSIT" | "LIVRE" | "ANNULE";

export type ColisCategorie =
  | "DOCUMENTS"
  | "VETEMENTS"
  | "ELECTRONIQUE"
  | "ALIMENTAIRE"
  | "FRAGILE"
  | "AUTRE";

export type ColisModalitePaiement = "A_LA_CONFIRMATION" | "A_LA_LIVRAISON";

export type TypeVehicule = "BERLINE" | "SUV" | "MINIBUS" | "BUS" | "MOTO";

export type TransactionType = "RECHARGE" | "REVERSEMENT" | "PAIEMENT" | "REMBOURSEMENT";
export type TransactionStatut = "EN_ATTENTE" | "REUSSI" | "ECHOUE" | "ANNULE";
export type TransactionOperateur = "MTN" | "MOOV" | "ORANGE" | "WALLET";

// ─── Utilisateurs ──────────────────────────────────────────────────────────

export interface UserRead {
  id: string;
  telephone: string;
  email: string | null;
  nom: string;
  prenom: string;
  photo_url: string | null;
  role: UserRole;
  statut: UserStatut;
  telephone_verifie: boolean;
  note_moyenne: number;
  nombre_avis: number;
  langue: string;
  created_at: string;
}

export type AdminUser = UserRead; // rôle ADMIN ou SUPER_ADMIN

export interface UserPublic {
  id: string;
  nom: string;
  prenom: string;
  photo_url: string | null;
  role: UserRole;
  note_moyenne: number;
  nombre_avis: number;
}

export interface UserUpdate {
  nom?: string;
  prenom?: string;
  email?: string;
  langue?: string;
}

// ─── Chauffeurs ────────────────────────────────────────────────────────────

export interface VehiculeRead {
  id: string;
  marque: string;
  modele: string;
  annee: number;
  immatriculation: string;
  couleur: string;
  type_vehicule: TypeVehicule;
  nombre_places: number;
  climatise: boolean;
  photo_url: string | null;
  actif: boolean;
}

export interface VehiculeCreate {
  marque: string;
  modele: string;
  annee: number;
  immatriculation: string;
  couleur: string;
  type_vehicule: TypeVehicule;
  nombre_places: number;
  climatise: boolean;
}

export interface ChauffeurRead {
  id: string;
  user_id: string;
  cin_numero: string | null;
  permis_numero: string | null;
  permis_expiration: string | null;
  kyc_valide: boolean;
  kyc_valide_le: string | null;
  autorisation_transfrontaliere: boolean;
  en_ligne: boolean;
  derniere_position_lat: number | null;
  derniere_position_lng: number | null;
  nombre_trajets: number;
  revenus_total: number;
  vehicules: VehiculeRead[];
}

export interface ChauffeurStats {
  nombre_trajets: number;
  revenus_total: number;
  note_moyenne: number;
  nombre_avis: number;
  en_ligne: boolean;
}

export interface ChauffeurRevenus {
  aujourd_hui: number;
  semaine: number;
  mois: number;
  total: number;
}

// ─── Voyages ───────────────────────────────────────────────────────────────

export interface VoyageRead {
  id: string;
  chauffeur_id: string;
  vehicule_id: string;
  ville_depart: string;
  ville_arrivee: string;
  point_depart: string;
  point_arrivee: string;
  date_depart: string;
  date_arrivee_estimee: string | null;
  prix_par_place: number;
  nombre_places_restantes: number;
  nombre_places_total: number;
  accepte_colis: boolean;
  climatise: boolean;
  non_fumeur: boolean;
  statut: VoyageStatut;
  distance_km: number | null;
  created_at: string;
}

export interface VoyageCreate {
  ville_depart: string;
  ville_arrivee: string;
  point_depart: string;
  point_arrivee: string;
  lat_depart: number;
  lng_depart: number;
  lat_arrivee: number;
  lng_arrivee: number;
  date_depart: string;
  prix_par_place: number;
  nombre_places_total: number;
  vehicule_id: string;
  accepte_colis?: boolean;
  climatise?: boolean;
  non_fumeur?: boolean;
}

export interface VoyageUpdate {
  prix_par_place?: number;
  point_depart?: string;
  date_depart?: string;
  accepte_colis?: boolean;
  non_fumeur?: boolean;
}

export interface VoyageSearchParams {
  ville_depart: string;
  ville_arrivee: string;
  date_depart: string;
  nombre_places?: number;
  accepte_colis?: boolean;
  climatise?: boolean;
  prix_max?: number;
  sort_by?: "depart_asc" | "depart_desc" | "prix_asc" | "prix_desc";
  page?: number;
  size?: number;
}

export interface ColisSearchParams {
  ville_depart: string;
  ville_arrivee: string;
  date_depart: string;
  sort_by?: "depart_asc" | "depart_desc" | "prix_asc" | "prix_desc";
  page?: number;
  size?: number;
}

// ─── Réservations ──────────────────────────────────────────────────────────

export interface VoyageEmbedded {
  id: string;
  ville_depart: string;
  ville_arrivee: string;
  date_depart: string;
  prix_par_place: number;
  statut: VoyageStatut;
}

export interface ReservationRead {
  id: string;
  voyage_id: string;
  client_id: string;
  nombre_places: number;
  prix_total: number;
  statut: ReservationStatut;
  code_confirmation: string;
  created_at: string;
  voyage: VoyageEmbedded | null;
  client: UserPublic | null;
}

export interface ReservationCreate {
  voyage_id: string;
  nombre_places: number;
}

// ─── Colis ─────────────────────────────────────────────────────────────────

export interface Colis {
  id: string;
  voyage_id: string;
  expediteur_id: string;
  ville_depart: string;
  ville_arrivee: string;
  description: string;
  categorie: ColisCategorie;
  poids_kg: number | null;
  fragile: boolean;
  destinataire_nom: string;
  destinataire_telephone: string;
  prix: number;
  modalite_paiement: ColisModalitePaiement;
  statut: ColisStatut;
  code_suivi: string;
  photo_url: string | null;
  voyage: VoyageRead | null;
  created_at: string;
  updated_at: string;
}

export interface ColisCreate {
  voyage_id: string;
  description: string;
  categorie: ColisCategorie;
  poids_kg?: number;
  fragile: boolean;
  destinataire_nom: string;
  destinataire_telephone: string;
  modalite_paiement?: ColisModalitePaiement;
}

// ─── Wallet & Transactions ──────────────────────────────────────────────────

export interface WalletRead {
  id: string;
  solde: number;
  devise: string;
  actif: boolean;
}

export interface TransactionRead {
  id: string;
  type: TransactionType;
  statut: TransactionStatut;
  operateur: TransactionOperateur;
  montant: number;
  created_at: string;
}

export interface RechargeInitiateRequest {
  montant: number;
  operateur: TransactionOperateur;
  telephone: string;
}

export interface WithdrawRequest {
  montant: number;
  telephone: string;
  operateur: TransactionOperateur;
}

export interface TransferRequest {
  destinataire_telephone: string;
  montant: number;
}

// ─── Avis ──────────────────────────────────────────────────────────────────

export interface AvisRead {
  id: string;
  auteur_id: string;
  cible_id: string;
  voyage_id: string;
  note: number;
  commentaire: string | null;
  tags: string[];
  signale: boolean;
  visible: boolean;
  created_at: string;
}

export interface AvisCreate {
  cible_id: string;
  voyage_id: string;
  note: number;
  commentaire?: string;
  tags?: string[];
}

// ─── Notifications ─────────────────────────────────────────────────────────

export interface NotificationRead {
  id: string;
  type: string;
  titre: string;
  corps: string;
  lue: boolean;
  data: Record<string, unknown> | null;
  created_at: string;
}

// ─── Admin ─────────────────────────────────────────────────────────────────

export interface AdminOverview {
  total_utilisateurs: number;
  total_voyages: number;
  total_colis: number;
}

// ─── Pagination ────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
```

---

## 17. Hooks TanStack Query

### 17.1 Setup QueryClient

```typescript
// src/main.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});
```

### 17.2 Query Keys centralisées

```typescript
// src/lib/query-keys.ts
export const keys = {
  auth: { me: () => ["auth", "me"] as const },
  users: {
    me: () => ["users", "me"] as const,
    detail: (id: string) => ["users", id] as const,
  },
  chauffeurs: {
    me: () => ["chauffeurs", "me"] as const,
    stats: () => ["chauffeurs", "me", "stats"] as const,
    revenus: () => ["chauffeurs", "me", "revenus"] as const,
    vehicules: () => ["chauffeurs", "me", "vehicules"] as const,
    detail: (id: string) => ["chauffeurs", id] as const,
  },
  voyages: {
    all: () => ["voyages"] as const,
    me: () => ["voyages", "me"] as const,
    popular: () => ["voyages", "popular"] as const,
    search: (params: object) => ["voyages", "search", params] as const,
    colisSearch: (params: object) => ["voyages", "colis-search", params] as const,
    detail: (id: string) => ["voyages", id] as const,
    reservations: (id: string, statut?: string) => ["voyages", id, "reservations", statut] as const,
    passagers: (id: string) => ["voyages", id, "passagers"] as const,
  },
  reservations: {
    me: () => ["reservations", "me"] as const,
    incoming: () => ["reservations", "incoming"] as const,
    detail: (id: string) => ["reservations", id] as const,
  },
  colis: {
    me: () => ["colis", "me"] as const,
    byVoyage: (voyageId: string) => ["colis", "voyage", voyageId] as const,
    detail: (id: string) => ["colis", id] as const,
  },
  wallet: {
    me: () => ["wallet", "me"] as const,
    activity: (page: number) => ["wallet", "activity", page] as const,
  },
  transactions: {
    me: (page: number) => ["transactions", "me", page] as const,
    detail: (id: string) => ["transactions", id] as const,
  },
  avis: {
    me: () => ["avis", "me"] as const,
    byChauffeur: (id: string, page: number) => ["avis", "chauffeur", id, page] as const,
  },
  notifications: {
    me: (page: number) => ["notifications", "me", page] as const,
    unreadCount: () => ["notifications", "unread-count"] as const,
  },
  admin: {
    overview: () => ["admin", "overview"] as const,
    users: () => ["admin", "users"] as const,
    pendingColis: () => ["admin", "colis", "pending"] as const,
  },
} as const;
```

### 17.3 Hooks Dashboard Admin

```typescript
// src/hooks/useAdmin.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { keys } from "@/lib/query-keys";
import { adminApi } from "@/lib/api/admin";

export const useAdminOverview = () =>
  useQuery({
    queryKey: keys.admin.overview(),
    queryFn: adminApi.overview,
    refetchInterval: 30_000,
  });

export const useAdminUsers = () =>
  useQuery({
    queryKey: keys.admin.users(),
    queryFn: adminApi.users,
  });

export const useAdminPendingColis = () =>
  useQuery({
    queryKey: keys.admin.pendingColis(),
    queryFn: adminApi.pendingColis,
    refetchInterval: 60_000,
  });

export const useSuspendUser = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => adminApi.suspendUser(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.admin.users() }),
  });
};

export const useValidateColis = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (colisId: string) => adminApi.validateColis(colisId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.admin.pendingColis() }),
  });
};
```

### 17.4 Hooks Voyages

```typescript
// src/hooks/useVoyages.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { keys } from "@/lib/query-keys";
import { voyagesApi } from "@/lib/api/voyages";
import type { VoyageSearchParams, ColisSearchParams } from "@/types/domain";

export const useVoyagesPopular = () =>
  useQuery({ queryKey: keys.voyages.popular(), queryFn: voyagesApi.popular });

export const useVoyagesSearch = (params: VoyageSearchParams, enabled = true) =>
  useQuery({
    queryKey: keys.voyages.search(params),
    queryFn: () => voyagesApi.search(params),
    enabled,
  });

export const useColisSearch = (params: ColisSearchParams, enabled = true) =>
  useQuery({
    queryKey: keys.voyages.colisSearch(params),
    queryFn: () => voyagesApi.colisSearch(params),
    enabled,
  });

export const useMyVoyages = () =>
  useQuery({ queryKey: keys.voyages.me(), queryFn: voyagesApi.me });

export const useVoyage = (id: string) =>
  useQuery({ queryKey: keys.voyages.detail(id), queryFn: () => voyagesApi.detail(id), enabled: !!id });

export const useVoyageReservations = (id: string, statut?: ReservationStatut) =>
  useQuery({
    queryKey: keys.voyages.reservations(id, statut),
    queryFn: () => voyagesApi.reservations(id, statut),
    enabled: !!id,
  });

export const useCreateVoyage = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: voyagesApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.voyages.me() }),
  });
};

export const useStartVoyage = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => voyagesApi.start(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: keys.voyages.detail(id) });
      qc.invalidateQueries({ queryKey: keys.voyages.me() });
    },
  });
};
```

### 17.5 Hooks Réservations

```typescript
// src/hooks/useReservations.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { keys } from "@/lib/query-keys";
import { reservationsApi } from "@/lib/api/reservations";

export const useMyReservations = () =>
  useQuery({ queryKey: keys.reservations.me(), queryFn: reservationsApi.me });

export const useIncomingReservations = () =>
  useQuery({
    queryKey: keys.reservations.incoming(),
    queryFn: reservationsApi.incoming,
    refetchInterval: 15_000,
  });

export const useReservation = (id: string) =>
  useQuery({
    queryKey: keys.reservations.detail(id),
    queryFn: () => reservationsApi.detail(id),
    enabled: !!id,
  });

export const useAcceptReservation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: reservationsApi.accept,
    onSuccess: (data) => {
      qc.setQueryData(keys.reservations.detail(data.id), data);
      qc.invalidateQueries({ queryKey: keys.reservations.incoming() });
    },
  });
};

export const useCreateReservation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: reservationsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.reservations.me() }),
  });
};
```

### 17.6 Hooks Colis

```typescript
// src/hooks/useColis.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { keys } from "@/lib/query-keys";
import { colisApi } from "@/lib/api/colis";

export const useMyColis = () =>
  useQuery({ queryKey: keys.colis.me(), queryFn: colisApi.me });

export const useColisByVoyage = (voyageId: string) =>
  useQuery({
    queryKey: keys.colis.byVoyage(voyageId),
    queryFn: () => colisApi.byVoyage(voyageId),
    enabled: !!voyageId,
  });

export const useColiDetail = (id: string) =>
  useQuery({
    queryKey: keys.colis.detail(id),
    queryFn: () => colisApi.detail(id),
    enabled: !!id,
  });

export const useCreateColis = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: colisApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.colis.me() }),
  });
};

export const useConfirmerColis = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => colisApi.confirmer(id),
    onSuccess: (data) => {
      qc.setQueryData(keys.colis.detail(data.id), data);
      qc.invalidateQueries({ queryKey: keys.colis.byVoyage(data.voyage_id) });
    },
  });
};
```

### 17.7 Hooks Wallet & Notifications

```typescript
// src/hooks/useWallet.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { keys } from "@/lib/query-keys";
import { get, post } from "@/lib/api";
import type { WalletRead, PaginatedResponse, TransactionRead } from "@/types/domain";

export const useWallet = () =>
  useQuery({ queryKey: keys.wallet.me(), queryFn: () => get<WalletRead>("/wallet/me") });

export const useWalletActivity = (page = 1) =>
  useQuery({
    queryKey: keys.wallet.activity(page),
    queryFn: () => get<PaginatedResponse<TransactionRead>>("/wallet/me/activity", { page }),
  });

// src/hooks/useNotifications.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { keys } from "@/lib/query-keys";
import { get, post, del } from "@/lib/api";
import type { PaginatedResponse, NotificationRead } from "@/types/domain";

export const useNotifications = (page = 1) =>
  useQuery({
    queryKey: keys.notifications.me(page),
    queryFn: () => get<PaginatedResponse<NotificationRead>>("/notifications/me", { page }),
  });

export const useUnreadCount = () =>
  useQuery({
    queryKey: keys.notifications.unreadCount(),
    queryFn: () => get<{ count: number }>("/notifications/me/unread-count"),
    refetchInterval: 30_000,
  });

export const useMarkAllRead = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => post("/notifications/me/read-all"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.notifications.unreadCount() });
      qc.invalidateQueries({ queryKey: ["notifications", "me"] });
    },
  });
};
```

---

## 18. Gestion des erreurs

### 18.1 Format uniforme des erreurs métier

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Identifiants invalides",
    "details": {},
    "request_id": "uuid-de-la-requête"
  }
}
```

Les erreurs de validation Pydantic (422) retournent :

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

### 18.2 Codes d'erreur complets

| Code | HTTP | Module | Description |
|------|------|--------|-------------|
| `PHONE_ALREADY_EXISTS` | 409 | Auth | Numéro déjà enregistré |
| `INVALID_CREDENTIALS` | 401 | Auth | Identifiants invalides |
| `ACCOUNT_SUSPENDED` | 403 | Auth | Compte suspendu |
| `TOKEN_INVALID` | 401 | Auth | Token JWT invalide ou révoqué |
| `INVALID_OTP` | 400 | Auth | Code OTP incorrect ou expiré |
| `OTP_MAX_ATTEMPTS` | 429 | Auth | Trop de tentatives OTP |
| `USER_NOT_FOUND` | 404 | Users | Utilisateur introuvable |
| `PERMISSION_DENIED` | 403 | Global | Action non autorisée |
| `KYC_NOT_VALIDATED` | 403 | Chauffeurs | KYC non validé |
| `VOYAGE_NOT_FOUND` | 404 | Voyages | Voyage introuvable |

### 18.3 Handler d'erreur global

```typescript
// src/lib/error-handler.ts
import { AxiosError } from "axios";
import { toast } from "sonner";

interface ApiError {
  error?: { code: string; message: string };
  detail?: string | Array<{ loc: string[]; msg: string }>;
}

export function handleApiError(error: unknown, fallback = "Une erreur est survenue"): string {
  if (error instanceof AxiosError) {
    const data = error.response?.data as ApiError | undefined;

    if (data?.error?.message) return data.error.message;

    if (typeof data?.detail === "string") return data.detail;

    if (Array.isArray(data?.detail)) {
      return data.detail.map((d) => d.msg).join(", ");
    }

    if (error.response?.status === 401) return "Session expirée — reconnectez-vous";
    if (error.response?.status === 403) return "Accès refusé";
    if (error.response?.status === 404) return "Ressource introuvable";
    if (error.response?.status === 409) return "Conflit — ressource déjà existante";
    if (error.response?.status === 422) return "Données invalides";
    if (error.response?.status === 429) return "Trop de tentatives — réessayez plus tard";
  }
  return fallback;
}

export function toastError(error: unknown, fallback?: string) {
  toast.error(handleApiError(error, fallback));
}
```

### 18.4 Utilisation dans les mutations

```typescript
const createColis = useCreateColis();

const handleSubmit = async (data: ColisCreate) => {
  try {
    const result = await createColis.mutateAsync(data);
    toast.success(`Colis créé — code : ${result.code_suivi}`);
    navigate(`/colis/${result.id}`);
  } catch (error) {
    toastError(error, "Impossible de créer le colis");
  }
};
```

---

## 19. Changelog v2.2 — ce qui a changé

### ⬆️ v2.1 → v2.2

#### Colis — tarification automatique

| Ce qui change | Action frontend |
|---------------|----------------|
| `prix` dans `ColisRead` n'est **plus jamais `null`** | Ne plus afficher un spinner en attente du prix après création |
| `modalite_paiement` est un **nouveau champ obligatoire** dans la réponse | Mettre à jour le type `Colis` |
| Le champ `modalite_paiement` est **optionnel** dans `ColisCreate` | Ajouter le sélecteur dans le formulaire (défaut `A_LA_LIVRAISON`) |

### ⬆️ v1 → v2.1

#### Réservations — données embedded

| Ce qui change | Action frontend |
|---------------|----------------|
| `ReservationRead` contient maintenant `voyage` et `client` | Supprimer les appels secondaires `GET /voyages/{id}` et `GET /users/{id}` après lecture d'une réservation |
| `accept/reject/cancel` retournent `ReservationRead` (plus `{ message }`) | Lire `response.statut` — ne plus lire `response.message` |

#### Voyages — nouvel endpoint colis

| Ce qui change | Action frontend |
|---------------|----------------|
| `GET /voyages/colis-search` retourne `PUBLIE` + `COMPLET` + `EN_COURS` | Utiliser **exclusivement** cet endpoint pour la recherche colis |
| `GET /voyages/search` reste inchangé (passagers uniquement) | Ne pas mélanger les deux endpoints |

#### Voyages — visibilité EN_COURS

| Ce qui change | Action frontend |
|---------------|----------------|
| Client peut accéder à un voyage `EN_COURS` s'il a une réservation active | Supprimer toute logique bloquant la navigation vers un voyage en cours |

#### Réservations — nouvel endpoint chauffeur

| Ajout | Utilisation |
|-------|-------------|
| `GET /voyages/{id}/reservations?statut=...` | Page "Détail voyage" chauffeur — onglets Demandes / Passagers |

---

## Annexe — Flux complets

### Flux A — Client réserve un voyage

```
1. GET /voyages/search?ville_depart=...&ville_arrivee=...&date_depart=...
2. GET /voyages/{id}                          — détail avant réservation
3. POST /reservations                          — EN_ATTENTE créé
4. [notification push WebSocket]
5. GET /reservations/me                        — voir statut mis à jour
6. POST /reservations/{id}/cancel              — si besoin
```

### Flux B — Chauffeur gère un voyage

```
1.  POST /chauffeurs/me/online
2.  POST /voyages                              — publier
3.  GET  /voyages/{id}/reservations?statut=EN_ATTENTE   — demandes
4.  POST /reservations/{id}/accept|reject
5.  GET  /voyages/{id}/passagers               — passagers confirmés
6.  GET  /colis/voyage/{id}                    — colis à transporter
7.  POST /voyages/{id}/start
8.  POST /colis/{id}/en_transit                — pour chaque colis
9.  POST /colis/{id}/livrer                    — à destination
10. POST /voyages/{id}/end
```

### Flux C — Client envoie un colis

```
1. GET  /voyages/colis-search?...             — PUBLIE + COMPLET + EN_COURS
2. POST /colis                                — prix calculé automatiquement dans la réponse
3. Afficher code_suivi + prix dans la confirmation
4. GET  /colis/{id}                           — polling statut
```

### Flux D — Suivi GPS en temps réel

```
1. GET /reservations/me                        — récupérer voyage_id
2. GET /voyages/{voyage_id}                    — statut EN_COURS
3. WS  /ws/tracking/voyage/{voyage_id}?token=... — position GPS
   Message : { type: "position_update", lat, lng, vitesse, heading, timestamp }
```

### Flux Admin — Validation KYC chauffeur

```
1. GET /admin/users                            — liste avec statut EN_ATTENTE_KYC
2. GET /chauffeurs/{id}                        — voir documents soumis
3. [Validation manuelle dans l'interface]
4. POST /admin/users/{id}/suspend              — si refus
   (endpoint de validation KYC admin à implémenter côté backend)
```

---

**Fin du guide.** Pour la structure du projet frontend, voir `WEB_REACT_JS.md`. Pour les migrations v1 → v2.1, voir `FRONTEND_MIGRATION_V2.md`. Pour la tarification colis, voir `COLIS_PRICING_INTEGRATION.md`.