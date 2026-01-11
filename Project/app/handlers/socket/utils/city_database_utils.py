import math
import requests

ONE_HOUR = 3600
EARTH_RADIUS_M = 6371000  # meters
FOOTBALL_FIELD_M = 100
TWELVE_FIELDS_M = 12 * FOOTBALL_FIELD_M  # 1200m
ONE_HOUR = 3600
from extensions import r as redis

import time
from extensions import r as redis

def set_home_location(phone, lat, lng):
    redis.hset(
        f"user:home:{phone}",
        mapping={
            "lat": lat,
            "lng": lng,
            "ts": int(time.time())
        }
    )

def get_home_location(phone):
    data = redis.hgetall(f"user:home:{phone}")
    if not data:
        return None

    return {
        "lat": float(data[b"lat"]),
        "lng": float(data[b"lng"]),
        "ts": int(data[b"ts"]),
    }



def add_to_city_bucket(role, city, client_id, lat, lng):
    if role == "rider":
        key = f"ride:city:riders:{city}"
    elif role == "vendor":
        key = f"ride:city:vendors:{city}"
    else:
        return

    member = f"{client_id}|{lat}|{lng}"

    redis.sadd(key, member)
    redis.expire(key, ONE_HOUR)


def get_city_bucket(role, city):
    key = f"ride:city:{role}s:{city}"
    members = redis.smembers(key)

    return [
        {
            "id": cid,
            "lat": float(lat),
            "lng": float(lng)
        }
        for cid, lat, lng in (
            m.decode().split("|") for m in members
        )
    ]

def distance_m(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = math.sin(dlat / 2)**2 + \
        math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def find_nearby_vendors(city, rider_lat, rider_lng, radius_m=TWELVE_FIELDS_M):
    vendors = get_city_bucket("vendor", city)

    nearby = []
    for v in vendors:
        d = distance_m(rider_lat, rider_lng, v["lat"], v["lng"])
        if d <= radius_m:
            nearby.append({
                "vendor_id": v["id"],
                "distance_m": round(d, 2),
                "lat": v["lat"],
                "lng": v["lng"]
            })

    # Optional: nearest first
    nearby.sort(key=lambda x: x["distance_m"])
    return nearby


def find_nearby_riders(city, vendor_lat, vendor_lng, radius_m=TWELVE_FIELDS_M):
    riders = get_city_bucket("rider", city)

    nearby = []
    for r in riders:
        d = distance_m(vendor_lat, vendor_lng, r["lat"], r["lng"])
        if d <= radius_m:
            nearby.append({
                "rider_id": r["id"],
                "distance_m": round(d, 2),
                "lat": r["lat"],
                "lng": r["lng"]
            })

    nearby.sort(key=lambda x: x["distance_m"])
    return nearby



def geocode_address(address: str):
    """
    Convert address to latitude & longitude using Nominatim
    """
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "adamu-whatsapp-bot/1.0 (contact: support@adamu.app)"
    }

    response = requests.get(url, params=params, headers=headers, timeout=10)

    if response.status_code != 200:
        return None

    data = response.json()

    if not data:
        return None

    return {
        "latitude": float(data[0]["lat"]),
        "longitude": float(data[0]["lon"]),
        "display_name": data[0]["display_name"]
    }

