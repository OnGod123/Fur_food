from flask import Blueprint, render_template, request, redirect, current_app, jsonify
from urllib.parse import quote
import requests
from app.handlers.login_as_guest import loginas_guest_bp
from app.handlers.phone_login import auth_bp_phone
from app.handlers.signup import signup_bp
from app.handlers.Google_login import auth_bp

home_bp = Blueprint("home_bp", __name__, template_folder="templates")


@home_bp.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return render_template("home.html")

    method = request.form.get("method", "").lower()
    user_phone = request.form.get("phone")
    whatsapp_bot_number = current_app.config.get("WHATSAPP_BOT_NUMBER", "2348000000000")
    default_message = f"Hello, I want to place an order. My WhatsApp contact: {user_phone or 'N/A'}"

    if method == "whatsapp":
        if not user_phone:
            # If no number, fallback to wa.me link
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

    # Redirect map for other methods
    redirect_map = {
        "phone": "auth_bp_phone.request_login_token",
        "guest": "auth_login_guest.login_guest",
        "google": "auth_bp.google_login",
        "signup": "signup_bp.signup_get",
    }

    if method in redirect_map:
        return redirect(url_for(redirect_map[method]))

    return "Please select a valid method", 400

