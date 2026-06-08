# GoTaxi — Tarification des colis & intégration mobile

> **Version API :** 2.2.0
> **Date :** 2026-05-04
> **Référence complète :** `API_VOYAGES_RESERVATIONS.md`

---

## Ce qui a changé

| Champ | Avant | Maintenant |
|-------|-------|------------|
| `prix` dans `ColisRead` | Toujours `null` | **Calculé automatiquement** à la création |
| `modalite_paiement` | Inexistant | Nouveau champ obligatoire dans `ColisCreate` |

---

## 1. Logique de tarification

Le prix est **calculé par le serveur** au moment de `POST /colis`. Le client mobile n'a pas à calculer quoi que ce soit — il reçoit le prix dans la réponse 201.

### Formule

```
prix = max(500, arrondi(
    distance_km × 3 FCFA × coeff_categorie
    + poids_kg  × 100 FCFA
    + supplément fragile
))
```

### Coefficients par catégorie

| Catégorie | Coefficient | Exemple 420 km, 3 kg |
|-----------|:-----------:|----------------------|
| `DOCUMENTS` | × 0.8 | 420×3×0.8 + 300 = **1 308 FCFA** |
| `VETEMENTS` | × 1.0 | 420×3×1.0 + 300 = **1 560 FCFA** |
| `ALIMENTAIRE` | × 1.1 | 420×3×1.1 + 300 = **1 686 FCFA** |
| `ELECTRONIQUE` | × 1.5 | 420×3×1.5 + 300 = **2 190 FCFA** |
| `FRAGILE` | × 1.5 | 420×3×1.5 + 300 = **2 190 FCFA** |
| `AUTRE` | × 1.0 | 420×3×1.0 + 300 = **1 560 FCFA** |

> **Supplément fragile :** +300 FCFA flat si `fragile: true`, quelle que soit la catégorie.
> **Prix plancher :** 500 FCFA — aucun colis ne peut coûter moins.

### Exemple concret

```
Cotonou → Parakou (420 km)
Catégorie : ELECTRONIQUE
Poids : 2 kg
Fragile : true

prix = 420 × 3 × 1.5 + 2 × 100 + 300
     = 1890 + 200 + 300
     = 2 390 FCFA
```

---

## 2. Modalité de paiement

Le client choisit **quand il paie** lors de la création du colis.

| Valeur | Signification | Quand déclencher le paiement côté mobile |
|--------|--------------|------------------------------------------|
| `A_LA_LIVRAISON` | Paiement à la livraison *(défaut)* | Quand le statut passe à `LIVRE` |
| `A_LA_CONFIRMATION` | Paiement quand le chauffeur accepte | Quand le statut passe à `CONFIRME` |

> Le champ `modalite_paiement` est **optionnel** dans `ColisCreate`. Si absent, le serveur applique `A_LA_LIVRAISON`.

---

## 3. Schéma `ColisCreate` mis à jour

### Request body — `POST /colis`

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

**Valeurs acceptées pour `categorie` :** `DOCUMENTS` · `VETEMENTS` · `ELECTRONIQUE` · `ALIMENTAIRE` · `FRAGILE` · `AUTRE`

**Valeurs acceptées pour `modalite_paiement` :** `A_LA_CONFIRMATION` · `A_LA_LIVRAISON`

---

## 4. Schéma `ColisRead` mis à jour

### Response — `POST /colis` (201) et `GET /colis/{id}`

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
  "voyage": { "...VoyageRead..." },
  "created_at": "2026-05-04T10:00:00Z",
  "updated_at": "2026-05-04T10:00:00Z"
}
```

**Différences vs ancienne réponse :**
- `prix` : plus jamais `null` à la création (valeur calculée par le serveur)
- `modalite_paiement` : nouveau champ toujours présent

---

## 5. Écran "Envoyer un colis" — flux recommandé

```
1. Rechercher un voyage disponible pour colis
   GET /voyages/colis-search?ville_depart=...&ville_arrivee=...&date_depart=...
   └── Afficher la liste des voyages (PUBLIE + COMPLET + EN_COURS)

2. L'utilisateur remplit le formulaire colis :
   ┌─────────────────────────────────────────────┐
   │ Description         [champ libre]           │
   │ Catégorie           [liste déroulante]      │
   │ Poids (kg)          [numérique]             │
   │ Fragile ?           [toggle]                │
   │ Destinataire nom    [champ]                 │
   │ Destinataire tél    [champ]                 │
   │ Paiement            [À la livraison ▼]      │
   └─────────────────────────────────────────────┘

   ⚠️ NE PAS afficher un champ "Prix" à remplir par l'utilisateur.
      Le prix est calculé automatiquement par le serveur.

3. POST /colis
   └── La réponse 201 contient `prix` calculé

4. Afficher la confirmation avec :
   - Code suivi : GTX-XXXXXX
   - Prix : 2 390 FCFA
   - Modalité : "Vous paierez à la livraison"
   - Statut : EN_ATTENTE (en attente d'acceptation du chauffeur)
```

---

## 6. Affichage du prix selon le statut

Le champ `modalite_paiement` détermine le message à afficher à l'utilisateur :

```
switch (colis.statut) {

  case "EN_ATTENTE":
    → "En attente d'acceptation du chauffeur"
    → Afficher prix estimé : "{colis.prix} FCFA"
    → Afficher : "Paiement {modalite_label} à la confirmation ou à la livraison"

  case "CONFIRME":
    if modalite_paiement == "A_LA_CONFIRMATION":
      → "Colis accepté — Paiement requis : {colis.prix} FCFA"
      → [Bouton : Payer maintenant]
    else:
      → "Colis accepté par le chauffeur — Paiement à la livraison"

  case "EN_TRANSIT":
    → "Colis en route"
    if modalite_paiement == "A_LA_LIVRAISON":
      → "Préparez {colis.prix} FCFA pour la livraison"

  case "LIVRE":
    if modalite_paiement == "A_LA_LIVRAISON":
      → "Colis livré — Paiement de {colis.prix} FCFA à effectuer"
      → [Bouton : Confirmer le paiement]
    else:
      → "Colis livré ✓"

  case "ANNULE":
    → "Colis annulé"
}
```

---

## 7. Vue chauffeur — affichage du colis

Sur l'écran `GET /colis/voyage/{voyage_id}`, afficher pour chaque colis :

```
┌──────────────────────────────────────────────┐
│ GTX-X7K2M4                      EN_ATTENTE   │
│ Kofi Mensah — +22967890123                   │
│ ELECTRONIQUE · 2 kg · Fragile ⚠️             │
│ Prix : 2 390 FCFA                            │
│ Paiement : À la livraison                    │
│                                              │
│  [Confirmer]            [Refuser]            │
└──────────────────────────────────────────────┘
```

---

## 8. Modèle TypeScript à mettre à jour

```typescript
// Ancien
interface ColisCreate {
  voyage_id: string
  description: string
  categorie: ColisCategorie
  poids_kg?: number
  fragile: boolean
  destinataire_nom: string
  destinataire_telephone: string
}

// Nouveau
type ColisModalitePaiement = 'A_LA_CONFIRMATION' | 'A_LA_LIVRAISON'

interface ColisCreate {
  voyage_id: string
  description: string
  categorie: ColisCategorie
  poids_kg?: number
  fragile: boolean
  destinataire_nom: string
  destinataire_telephone: string
  modalite_paiement?: ColisModalitePaiement  // défaut serveur : A_LA_LIVRAISON
}

interface Colis {
  id: string
  voyage_id: string
  expediteur_id: string
  ville_depart: string
  ville_arrivee: string
  description: string
  categorie: ColisCategorie
  poids_kg: number | null
  fragile: boolean
  destinataire_nom: string
  destinataire_telephone: string
  prix: number           // ← plus jamais null à la création
  modalite_paiement: ColisModalitePaiement  // ← NOUVEAU
  statut: ColisStatut
  code_suivi: string
  photo_url: string | null
  voyage: Voyage | null
  created_at: string
  updated_at: string
}
```

---

## 9. Aucun changement sur les autres endpoints colis

Ces endpoints fonctionnent exactement comme avant :

- `GET /colis/me` — liste des colis du client
- `GET /colis/voyage/{voyage_id}` — colis d'un voyage (chauffeur)
- `GET /colis/{colis_id}` — détail d'un colis
- `POST /colis/{id}/confirmer` — chauffeur accepte
- `POST /colis/{id}/en_transit` — chauffeur met en route
- `POST /colis/{id}/livrer` — chauffeur livre
- `POST /colis/{id}/annuler` — annulation

La réponse de tous ces endpoints inclut maintenant `prix` (non null) et `modalite_paiement`.