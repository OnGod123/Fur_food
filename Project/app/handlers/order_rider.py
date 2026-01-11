from flask import Blueprint, request, jsonify
from app.extensions import socketio, session_scope, redis_client
from app.database.user_models import User, RiderAndStrawler
from app.merchants.Database.rideshare import RideShare
from geopy.geocoders import Nominatim
from datetime import datetime
from app.utils.jwt_tokens.verify_user import verify_jwt_token
from app.handler.socket.utils.city_database_utils import geocode_address

TWELVE_FIELDS_M = 1320  
GLOBAL_ROOM = "all_participants"
order_ride_bp = Blueprint("delivery_bp", __name__)
geolocator = Nominatim(user_agent="rideshare_app")

@order_ride_bp.route("/user/order_ride", methods=["POST"])
@verify_jwt_token
def order_ride(user):
    """
    User places a ride request.
    """
    data = request.get_json() or {}
    mode = data.get("mode")
    destination = data.get("Pickup_destination")

    if not destination:
        return jsonify({"error": "Destination address required"}), 400

    
    user_send_coordinate = {
        "user_id": user.id,
        "username": getattr(user, "username", ""),
        "user_name": getattr(user, "name", ""),
        "phone": getattr(user, "phone", ""),
        "destination": destination,
        "created_at": str(datetime.utcnow())
    }


    if mode == "manual":
         address = data.get("address")
        if not address:
            return jsonify({"error": "Pickup address required"}), 400

        location = geocode_address(address)

        if not location:
            return jsonify({
                "error": "Address not found. Please send a clear, locatable address."
         }), 400

        user_send_coordinate.update({
            "pickup_address": location["display_name"],
            "latitude": location["latitude"],
            "longitude": location["longitude"]
         })
    elif mode == "auto":
        lat = data.get("latitude")
        lng = data.get("longitude")
        if lat is None or lng is None:
            return jsonify({"error": "Coordinates required"}), 400
        location = geolocator.reverse(f"{lat}, {lng}", language="en")
        if not location:
            return jsonify({"error": "Could not resolve pickup location"}), 400
        user_send_coordin:ate.update({
            "pickup_address": location.address,
            "latitude": lat,
            "longitude": lng
        })
    else:
        return jsonify({"error": "Invalid mode"}), 400


    with session_scope() as session:
        ride = Order_Ride(
            user_id=user.id,
            pickup_address=user_send_coordinate["pickup_address"],
            pickup_latitude=user_send_coordinate.get("latitude"),
            pickup_longitude=user_send_coordinate.get("longitude"),
            destination_address=destination,
            status="pending",
            created_at=datetime.utcnow()
        )
        session.add(ride)
        session.flush()
        ride_id = ride.id

    user_send_coordinate["ride_id"] = ride_id

    
    socketio.emit(
        "new_ride_request",
        user_send_coordinate,
        room=GLOBAL_ROOM,
        namespace="/global"
    )

    
    if user_send_coordinate.get("latitude") and user_send_coordinate.get("longitude"):
        addr = location.raw.get("address", {})
        city = addr.get("city") or addr.get("town") or addr.get("state")
        nearby_riders = find_nearby_riders(
            city = city,  
            vendor_lat=user_send_coordinate["latitude"],
            vendor_lng=user_send_coordinate["longitude"]
        )
    else:
        nearby_riders = []

    
    matched_data = {
        "user": user_send_coordinate,
        "riders": [],
        "vendors": []  
    }


    for r in nearby_riders:
        notif_dict = {
            "order_id": ride_id,
            "type": "RIDE_MATCH",
            "payload": {
                "pickup": user_send_coordinate["pickup_address"],
                "destination": destination,
                "user_phone": user_send_coordinate["phone"],
                "username": user_send_coordinate["username"]
            }
        }
        matched_data["riders"].append({
            "rider_id": r["rider_id"],
            "distance_m": r["distance_m"]
        })

        rider_obj = get_rider_by_id(r["rider_id"])  
        if rider_obj:
            send_whatsapp_message(rider_obj.phone, notif_dict)


    redis_client.setex(f"ride:match:{ride_id}", 3600, json.dumps(matched_data))

    return jsonify({
        "message": "Ride request placed successfully",
        "ride_id": ride_id,
        "matched_riders": matched_data["riders"]
    }), 201

