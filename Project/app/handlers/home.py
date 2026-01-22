from flask import Blueprint, render_template, request, redirect, current_app, jsonify
from urllib.parse import quote
import requests
from app.handlers.login_as_guest import loginas_guest_bp
from app.handlers.phone_login import auth_bp_phone
from app.handlers.signup import signup_bp
from app.handlers.Google_login import auth_bp
from app.handlers.socket.utils.city_database_utils import set_home_location

home_bp = Blueprint("home", __name__, template_folder="../templates/html")

@home_bp.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return render_template("home.html")

    method = request.form.get("method", "").lower()
    user_phone = request.form.get("phone")
    coordinates = request.form.get("coordinates")  # expects "lat,lng" as string, e.g., "40.73,-73.93"
    location_address = None

    # Parse and reverse-geocode the coordinates if provided
    if coordinates:
        try:
            lat_str, lng_str = coordinates.split(",", 1)
            lat, lng = float(lat_str.strip()), float(lng_str.strip())
            set_home_location(user_phone, lat, lng)
            location = geolocator.reverse((lat, lng), language='en')
            if location and location.address:
                location_address = location.address
        except Exception as e:
            location_address = None  # Could log the error

    whatsapp_bot_number = current_app.config.get("WHATSAPP_BOT_NUMBER", "2348000000000")

    default_message_parts = [
        "Hello, I want to place an order.",
        f"My WhatsApp contact: {user_phone or 'N/A'}"
    ]
    if location_address:
        default_message_parts.append(f"You are at this destination: {location_address}")
    default_message = " ".join(default_message_parts)

    if method == "whatsapp":
        if not user_phone:
            whatsapp_url = f"https://wa.me/{whatsapp_bot_number}?text={quote(default_message)}"
            return redirect(whatsapp_url)

        access_token = current_app.config.get("WHATSAPP_ACCESS_TOKEN")
        phone_number_id = current_app.config.get("WHATSAPP_PHONE_NUMBER_ID")
        if not access_token or not phone_number_id:
            return "WhatsApp API credentials not configured", 500

        url = f"https://graph.facebook.com/v24.0/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": user_phone,
            "type": "text",
            "text": {"body": default_message, "preview_url": False},
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.ok:
                return jsonify({"message": "WhatsApp message sent", "response": response.json()})
            else:
                return jsonify({"error": "Failed to send WhatsApp message", "details": response.json()}), 500
        except requests.RequestException as e:
            return jsonify({"error": "Request failed", "details": str(e)}), 500

    redirect_map = {
        "phone": "auth_bp_phone.request_login_token",
        "guest": "auth_login_guest.login_guest",
        "google": "auth_bp.google_login",
        "signup": "signup_bp.signup_get",
    }
    if method in redirect_map:
        return redirect(url_for(redirect_map[method]))

    return "Please select a valid method", 400
