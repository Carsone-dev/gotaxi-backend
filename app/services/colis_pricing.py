"""
Tarification des colis GoTaxi.

Formule :
    prix = max(PRIX_MIN, distance_km × TARIF_KM × coeff_categorie
                         + poids_kg × TARIF_KG
                         + supplément fragile)

Toutes les constantes sont en FCFA et peuvent être ajustées sans toucher
à la logique.
"""

import math
from app.models.colis import ColisCategorie

# ── Constantes tarifaires ───────────────────────────────────────────────────

TARIF_KM: float = 3.0        # FCFA par km (base trajet)
TARIF_KG: float = 100.0      # FCFA par kg
SUPPLEMENT_FRAGILE: float = 300.0  # FCFA flat si fragile=True
PRIX_MIN: float = 500.0      # Prix plancher quel que soit le calcul

# Multiplicateur appliqué au coût distance selon la catégorie
_COEFF_CATEGORIE: dict[ColisCategorie, float] = {
    ColisCategorie.DOCUMENTS:    0.8,   # léger, pas de contrainte
    ColisCategorie.VETEMENTS:    1.0,   # standard
    ColisCategorie.ALIMENTAIRE:  1.1,   # nécessite des précautions
    ColisCategorie.ELECTRONIQUE: 1.5,   # valeur élevée
    ColisCategorie.FRAGILE:      1.5,   # manipulation délicate
    ColisCategorie.AUTRE:        1.0,
}


# ── Utilitaire distance ─────────────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance à vol d'oiseau entre deux coordonnées GPS (en km)."""
    R = 6_371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ── Calcul principal ────────────────────────────────────────────────────────

def calculer_prix_colis(
    *,
    categorie: ColisCategorie,
    poids_kg: float | None,
    fragile: bool,
    distance_km: int | None,
    lat_depart: float,
    lng_depart: float,
    lat_arrivee: float,
    lng_arrivee: float,
) -> float:
    """Retourne le prix en FCFA, arrondi à l'entier le plus proche."""
    dist = float(distance_km) if distance_km else haversine_km(
        lat_depart, lng_depart, lat_arrivee, lng_arrivee
    )
    coeff = _COEFF_CATEGORIE.get(categorie, 1.0)
    poids = float(poids_kg) if poids_kg else 0.0

    prix = dist * TARIF_KM * coeff + poids * TARIF_KG
    if fragile:
        prix += SUPPLEMENT_FRAGILE

    return max(PRIX_MIN, round(prix))