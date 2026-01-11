from flask_socketio import Namespace, emit, join_room
from flask import request, g
from datetime import datetime
from geopy.geocoders import Nominatim
import json

from app.extensions import redis
from app.rooms import GLOBAL_ROOM, city_room
from app.jwt_utils.identify import identify_token

geolocator = Nominatim(user_agent="rideshare_app")


class GlobalNamespace(Namespace):
    namespace = "/global"

    # ---------- CONNECT ----------
    def on_connect(self):
        token = request.headers.get("Authorization") or request.args.get("token")

        if not token:
            return False

        if token.startswith("Bearer "):
            token = token.split(" ")[1]

        try:
            result = identify_token(token)
            g.client_id = result["payload"]["id"]
            g.client_type = result["type"]   # user | rider
        except Exception:
            return False

        join_room(GLOBAL_ROOM)

        emit("connected", {
            "user_id": g.client_id,
            "role": g.client_type
        })

    #____send_cordinate______
def on_send_ride_coordinate(self, data):
    client_id = g.client_id
    role = g.client_type  # "user" | "rider" | "vendor"
    timestamp = datetime.utcnow().isoformat()

    # ------------------------------------------------
    # 0️⃣ NORMALIZE INPUT (THIS WAS MISSING)
    # ------------------------------------------------
    if role == "user":
        payload = data.get("user_send_coordinate", {})
    else:
        payload = data.get("coordinate", {})

    lat = payload.get("lat")
    lng = payload.get("lng")
    ride_id = payload.get("ride_id") if role == "user" else None

    if lat is None or lng is None:
        emit("error", {"message": "Coordinates required"})
        return

    # ------------------------------------------------
    # 1️⃣ REVERSE GEO
    # ------------------------------------------------
    location = geolocator.reverse(f"{lat}, {lng}", language="en")
    if not location:
        emit("error", {"message": "Location resolve failed"})
        return

    addr = location.raw.get("address", {})
    city = addr.get("city") or addr.get("town") or addr.get("state")
    street = addr.get("road") or addr.get("street") or "unknown"

    if not city:
        emit("error", {"message": "City not resolved"})
        return

    # ------------------------------------------------
    # 2️⃣ STORE LOCATION BY ROLE (SEPARATE STORES)
    # ------------------------------------------------
    base_location = {
        "id": client_id,
        "lat": lat,
        "lng": lng,
        "city": city,
        "street": street,
        "ts": timestamp
    }

    if role == "user":
        base_location["ride_id"] = ride_id
        redis.hset(f"ride:user:location:{client_id}", mapping=base_location)

    elif role == "rider":
        redis.hset(f"ride:rider:location:{client_id}", mapping=base_location)
        redis.sadd("ride:riders:ids", client_id)
        add_to_city_bucket("rider", city, client_id, lat, lng)

    elif role == "vendor":
        redis.hset(f"ride:vendor:location:{client_id}", mapping=base_location)
        redis.sadd("ride:vendors:ids", client_id)
        add_to_city_bucket("rider", city, client_id, lat, lng)

    # ------------------------------------------------
    # 3️⃣ INDEX RIDERS & VENDORS ONLY
    # ------------------------------------------------
    if role in ("rider", "vendor"):
        redis.sadd(f"ride:index:street:{city}:{street}", client_id)
        redis.sadd(f"ride:index:city:{city}", client_id)

        emit("location_registered", {
            "role": role,
            "city": city,
            "street": street
        })
        return

    # ------------------------------------------------
    # 4️⃣ USER → MATCH RIDERS & VENDORS
    # ------------------------------------------------
    matched_ids = []
    seen = set()

    # Priority 1: street
    for pid in redis.smembers(f"ride:index:street:{city}:{street}"):
        pid = pid.decode()
        if pid not in seen:
            seen.add(pid)
            matched_ids.append(pid)
        if len(matched_ids) >= 20:
            break

    # Priority 2: city
    if len(matched_ids) < 40:
        for pid in redis.smembers(f"ride:index:city:{city}"):
            pid = pid.decode()
            if pid not in seen:
                seen.add(pid)
                matched_ids.append(pid)
            if len(matched_ids) >= 40:
                break

    # ------------------------------------------------
    # 5️⃣ BUILD MATCHED_DATA (STRICT STRUCTURE)
    # ------------------------------------------------
    matched_data = {
        "user": base_location,
        "riders": [],
        "vendors": []
    }

    for pid in matched_ids:
        rdata = redis.hgetall(f"ride:rider:location:{pid}")
        if rdata:
            matched_data["riders"].append({
                "id": pid,
                "lat": rdata[b"lat"].decode(),
                "lng": rdata[b"lng"].decode(),
                "street": rdata[b"street"].decode(),
                "city": rdata[b"city"].decode()
            })
            continue

        vdata = redis.hgetall(f"ride:vendor:location:{pid}")
        if vdata:
            matched_data["vendors"].append({
                "id": pid,
                "lat": vdata[b"lat"].decode(),
                "lng": vdata[b"lng"].decode(),
                "street": vdata[b"street"].decode(),
                "city": vdata[b"city"].decode()
            })

    # ------------------------------------------------
    # 6️⃣ STORE + EMIT
    # ------------------------------------------------
    redis.hset(
        f"ride:order:matching:{client_id}",
        mapping={"data": json.dumps(matched_data)}
    )

    for p in matched_data["riders"] + matched_data["vendors"]:
        emit(
            "new_service_request",
            matched_data,
            room=str(p["id"]),
            namespace="/global"
        )

    emit("location_registered", {
        "role": "user",
        "matched_riders": len(matched_data["riders"]),
        "matched_vendors": len(matched_data["vendors"]),
        "city": city,
        "street": street
    })


   # ---------- GROUP MESSAGE ----------
      def on_send_group_message(self, data):
        message = data.get("message")
        if not message:
            emit("error", {"message": "Message required"})
            return

        live = redis.hgetall(f"ride:live:{g.client_id}")
        if not live:
            emit("error", {"message": "Location not registered"})
            return

        city = live[b"city"].decode()
        room = city_room(city)

        payload = {
            "sender_id": g.client_id,
            "sender_role": g.client_type,
            "message": message,
            "city": city,
            "ts": datetime.utcnow().isoformat() + "Z"
        }

        redis.rpush(f"chat:history:{city}", json.dumps(payload))

        emit("group_message", payload, room=GLOBAL_ROOM)


def on_send_errand_coordinate(self, data):
    client_id = g.client_id
    role = g.client_type   # "user" | "rider" | "vendor"
    ts = datetime.utcnow().isoformat()

    # ----------------------------------
    # 0️⃣ Normalize input
    # ----------------------------------
    payload = (
        data.get("user_send_coordinate", {})
        if role == "user"
        else data.get("coordinate", {})
    )

    lat = payload.get("lat")
    lng = payload.get("lng")

    if lat is None or lng is None:
        emit("error", {"message": "Coordinates required"})
        return

    destination = payload.get("destination") if role == "user" else None

    # ----------------------------------
    # 1️⃣ Reverse geo (pickup)
    # ----------------------------------
    city, street = reverse_geo(lat, lng)
    if not city:
        emit("error", {"message": "Pickup city not resolved"})
        return

    # ----------------------------------
    # 2️⃣ Destination resolve (user only)
    # ----------------------------------
    dest_city = None
    if role == "user" and destination:
        dest_city = resolve_destination(destination)
        if not dest_city:
            emit("error", {"message": "Destination not resolved"})
            return

    # ----------------------------------
    # 3️⃣ Base location object
    # ----------------------------------
    base_location = {
        "id": client_id,
        "lat": lat,
        "lng": lng,
        "city": city,
        "street": street,
        "ts": ts,
    }

    if dest_city:
        base_location["dest_city"] = dest_city

    # ----------------------------------
    # 4️⃣ Store by role
    # ----------------------------------
    if role == "user":
        redis.hset(
            f"ride:user:location:{client_id}",
            mapping=base_location
        )

    elif role == "rider":
        redis.hset(
            f"ride:rider:location:{client_id}",
            mapping=base_location
        )

    elif role == "vendor":
        redis.hset(
            f"ride:vendor:location:{client_id}",
            mapping=base_location
        )

    # ----------------------------------
    # 5️⃣ Index riders/vendors only
    # ----------------------------------
    if role in ("rider", "vendor"):
        redis.sadd(f"ride:index:pickup:street:{city}:{street}", client_id)
        redis.sadd(f"ride:index:pickup:city:{city}", client_id)
        redis.sadd(f"ride:index:dest:city:{city}", client_id)

        emit("location_registered", {
            "role": role,
            "city": city,
            "street": street
        })
        return

    # ----------------------------------
    # 6️⃣ USER → MATCHING
    # ----------------------------------
    matched_ids = []
    seen = set()

    # ① Pickup street
    for pid in redis.smembers(f"ride:index:pickup:street:{city}:{street}"):
        pid = pid.decode()
        if pid not in seen:
            seen.add(pid)
            matched_ids.append(pid)

    # ② Pickup city
    for pid in redis.smembers(f"ride:index:pickup:city:{city}"):
        pid = pid.decode()
        if pid not in seen:
            seen.add(pid)
            matched_ids.append(pid)

    # ③ Destination city
    if dest_city:
        for pid in redis.smembers(f"ride:index:dest:city:{dest_city}"):
            pid = pid.decode()
            if pid not in seen:
                seen.add(pid)
                matched_ids.append(pid)

    matched_ids = matched_ids[:40]

    # ----------------------------------
    # 7️⃣ Build matched_data
    # ----------------------------------
    matched_data = {
        "user": base_location,
        "riders": [],
        "vendors": []
    }

    for pid in matched_ids:
        rdata = redis.hgetall(f"ride:rider:location:{pid}")
        if rdata:
            matched_data["riders"].append({
                "id": pid,
                "lat": rdata[b"lat"].decode(),
                "lng": rdata[b"lng"].decode(),
                "city": rdata[b"city"].decode(),
                "street": rdata[b"street"].decode(),
            })
            continue

        vdata = redis.hgetall(f"ride:vendor:location:{pid}")
        if vdata:
            matched_data["vendors"].append({
                "id": pid,
                "lat": vdata[b"lat"].decode(),
                "lng": vdata[b"lng"].decode(),
                "city": vdata[b"city"].decode(),
                "street": vdata[b"street"].decode(),
            })

    # ----------------------------------
    # 8️⃣ Persist match snapshot
    # ----------------------------------
    redis.hset(
        f"ride:order:matching:{client_id}",
        mapping={"data": json.dumps(matched_data)}
    )

    # ----------------------------------
    # 9️⃣ Emit to matched riders/vendors
    # ----------------------------------
    for p in matched_data["riders"] + matched_data["vendors"]:
        emit(
            "new_service_request",
            matched_data,
            room=str(p["id"]),
            namespace="/global"
        )

    # ----------------------------------
    # 🔟 Ack user
    # ----------------------------------
    emit("location_registered", {
        "role": "user",
        "matched_riders": len(matched_data["riders"]),
        "matched_vendors": len(matched_data["vendors"]),
        "pickup_city": city,
        "destination_city": dest_city
    })

