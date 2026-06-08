import math


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_duration_hours(distance_km: float, avg_speed_kmh: float = 80.0) -> float:
    return distance_km / avg_speed_kmh


def estimate_price(distance_km: float, base_price_per_km: int = 50) -> int:
    return max(500, int(distance_km * base_price_per_km))