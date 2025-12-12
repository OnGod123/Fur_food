from flask import Blueprint, render_template, request, redirect, current_app, jsonify
from urllib.parse import quote
import requests

home_bp = Blueprint("home_bp", __name__, template_folder="templates")


@home_bp.route("/", methods=["GET", "POST"])
def home():
    """
    Home page:
    - GET: render selection form
    - POST: process selected method
    """
    if request.method == "GET":
        # Render simple HTML selection form
        return render_template("home.html")

    # POST: process selection
    method = request.form.get("method", "").lower()
    user_phone = request.form.get("phone")  
    wa_url = f"https://wa.me/{whatsapp_bot_number}"

    if method == "whatsapp":
        whatsapp_bot_number = current_app.config.get("WHATSAPP_BOT_NUMBER", "2348000000000")
        default_message = (
            f"Hello, I want to place an order. My WhatsApp contact: {user_phone or 'N/A'}"
        )

        if user_phone:
            # WhatsApp Cloud API
            access_token = current_app.config.get("WHATSAPP_ACCESS_TOKEN")
            phone_number_id = current_app.config.get("WHATSAPP_PHONE_NUMBER_ID")

        else:
            return jsonify(
                    {"error": "insert you whatsapp number for this method", "details": response.json()}
                ), 500 
       

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

            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.ok:
                return jsonify({"message": "WhatsApp message sent", "response": response.json()})
            else:
                return jsonify(
                    {"error": "Failed to send WhatsApp message", "details": response.json()}
                ), 500
        else:
            # Redirect user to wa.me link if phone not provided
            whatsapp_url = f"https://wa.me/{whatsapp_bot_number}?text={quote(default_message)}"
            return redirect(wa_url)

    elif method == "phone":
        return redirect(url_for("blueprint_name.endpoint_name"))

    elif method == "guest":
        return redirect(url_for("blueprint_name.endpoint_name"))

    elif method == "google":
        return redirect(url_for("blueprint_name.endpoint_name"))

    elif method == "signup":
        return redirect(url_for("blueprint_name.endpoint_name"))


    return "Please select a valid method", 400