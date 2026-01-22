import uuid
import hmac
import hashlib
from functools import wraps
from flask import Blueprint, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.whatsapp.watsapphandler import WhatsAppClient,  WhatsAppFlow
from flask import Blueprint, render_template, request

bp_whatsapp = Blueprint("whatsapp", __name__, url_prefix="/whatsapp")

def verify_whatsapp_signature(raw_body: bytes, signature_header: str, app_secret: str) -> bool:
    if not signature_header or not app_secret:
        return False
    prefix = 'sha256='
    if not signature_header.startswith(prefix):
        return False
    sig_hex = signature_header[len(prefix):]
    mac = hmac.new(app_secret.encode('utf-8'), msg=raw_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig_hex)


@bp_whatsapp.route("", methods=["POST"])
def whatsaphandlers():
    raw_body = request.get_data()
    signature = request.headers.get('X-Hub-Signature-256') or request.headers.get('x-hub-signature-256')
    app_secret = current_app.config.get('WHATSAPP_APP_SECRET')

    # --- VERIFY ---
    if app_secret:
        if not verify_whatsapp_signature(raw_body, signature, app_secret):
            current_app.logger.warning("Invalid webhook signature")
            return 'Invalid signature', 401

    # --- EXTRACT MESSAGE (UNCHANGED) ---
    payload = request.get_json(force=True)
    phone = payload.get("from")
    text = payload.get("text", {}).get("body", "").strip()

    if not phone:
        return "Missing phone", 400

    sender = WhatsAppClient(
        token=current_app.config["WHATSAPP_TOKEN"],
        phone_number_id=current_app.config["META_PHONE_NUMBER_ID"],
        api_version=current_app.config["META_API_VERSION"],
    )

    flow = WhatsAppFlow(phone, text, sender)
    return flow.run()


@bp_whatsapp.route('/webhook', methods=['GET'])
def verify_whatsapp():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    expected = current_app.config.get('WHATSAPP_VERIFY_TOKEN')

    if mode == 'subscribe' and token and expected and token == expected:
        return challenge, 200

    return 'Forbidden', 403

