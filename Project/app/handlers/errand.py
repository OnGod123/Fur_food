from flask import Blueprint, render_template, request, redirect, current_app, jsonify
from app.extensions import socketio, session_scope, redis_client
from app.Database.user_models import User
from app.Database.RiderAndStrawler import RiderAndStrawler
from app.Database.errand import Errand
from geopy.geocoders import Nominatim
from datetime import datetime
from app.utils.jwt_tokens.verify_user import verify_jwt_token
from app.extensions import geolocator
import json

TWELVE_FIELDS_M = 1320

send_errand_bp = Blueprint("send-errand", __name__)

@send_errand_bp.route("/user/send_errand", methods=["POST"])
@verify_jwt_token
def send_errand(user):
    """
    User sends an errand.
    """
    data = request.get_json() or {}
    description = data.get("description")
    destination = data.get("destination")
    mode = data.get("mode")

    if not description:
        return jsonify({"error": "Errand description required"}), 400
    if not destination:
        return jsonify({"error": "Destination required"}), 400
    if mode not in ("manual", "auto"):
        return jsonify({"error": "Mode must be 'manual' or 'auto'"}), 400

    pickup_address = data.get("address")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    
    user_send_errand = {
        "user_id": user.id,
        "user_name": getattr(user, "name", ""),
        "user_phone": getattr(user, "phone", ""),
        "description": description,
        "destination": destination,
        "created_at": datetime.utcnow().isoformat()
    }

    try:
        
        if pickup_address:
            location = geolocator.geocode(pickup_address)
            location_1 = geolocator.reverse(f"{latitude}, {longitude}", language="en")
            addr = location_1.raw.get("address", {})
            city = addr.get("city") or addr.get("town") or addr.get("state")
            if not location:
                return jsonify({"error": "Invalid pickup address"}), 400
            user_send_errand.update({
                "pickup_address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude
            })

        
        elif latitude is not None and longitude is not None:
            location = geolocator.reverse(f"{latitude}, {longitude}", language="en")
            addr = location.raw.get("address", {})
            city = addr.get("city") or addr.get("town") or addr.get("state")
            if not location:
                return jsonify({"error": "Could not resolve pickup location"}), 400
            user_send_errand.update({
                "pickup_address": location.address,
                "latitude": latitude,
                "longitude": longitude
            })
        else:
            return jsonify({"error": "Pickup address or coordinates required"}), 400

    except Exception as e:
        return jsonify({"error": f"Geocoding error: {str(e)}"}), 500

    
    with session_scope() as session:
        errand = Errand(
            user_id=user.id,
            description=description,
            pickup_address=user_send_errand["pickup_address"],
            pickup_latitude=user_send_errand["latitude"],
            pickup_longitude=user_send_errand["longitude"],
            destination=destination,
            created_at=datetime.utcnow()
        )
        session.add(errand)
        session.flush()
        errand_id = errand.id

    user_send_errand["errand_id"] = errand_id

    
    socketio.emit(
        "new_errand_request",
        user_send_errand,
        room=GLOBAL_ROOM, 
         namespace="/global"
    )

    
    nearby_riders = find_nearby_riders(
        city=city,
        lat=user_send_errand["latitude"],
        lng=user_send_errand["longitude"]
    )

    
    matched_data = {
        "user": user_send_errand,
        "riders": []
    }

    for r in nearby_riders:
        notif_payload = {
            "order_id": errand_id,
            "type": "ERRAND_MATCH",
            "payload": {
                "pickup": user_send_errand["pickup_address"],
                "destination": destination,
                "description": description,
                "user_phone": user_send_errand["user_phone"]
            }
        }
        matched_data["riders"].append({
            "rider_id": r["rider_id"],
            "distance_m": r["distance_m"]
        })

        
        rider_obj = get_rider_by_id(r["rider_id"])
        if rider_obj:
            send_whatsapp_message(rider_obj.phone, notif_payload)

    
    redis_client.setex(f"errand:match:{errand_id}", 3600, json.dumps(matched_data))

    return jsonify({
        "message": "Errand sent successfully",
        "errand_id": errand_id,
        "matched_riders": matched_data["riders"]
    }), 201

