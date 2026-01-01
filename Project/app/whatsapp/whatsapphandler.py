import uuid
import hmac
import hashlib
import requests

from functools import wraps
from flask import Blueprint, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.whatsapp.utils.session import load_session, save_session, clear_session
from app.whatsapp.utils import format_summary
from app.orders.validator import validate_items
from app.services.order_service import build_order
from app.payments.wallet import try_wallet_pay
from app.handlers.single_central_pay import build_payment_link
from app.websocket.vendor_notify import notify_vendor_new_order
from app.delivery.create import create_delivery
from app.delivery.redirect import redirect_to_bargain
from app.ai.parsers import ai_parse_items, ai_parse_address
from app.database.models import User, Vendor
from app import ws





class WhatsAppClient:
    def __init__(self, token: str, phone_number_id: str, api_version: str):
        if not token or not phone_number_id:
            raise ValueError("WHATSAPP_TOKEN and META_PHONE_NUMBER_ID must be set")
        self.token = token
        self.phone_number_id = phone_number_id
        self.api_version = api_version
        self.base = f"https://graph.facebook.com/{self.api_version}"

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def send_text(self, to: str, message: str, timeout: int = 10):
        url = f"{self.base}/{self.phone_number_id}/messages"
        payload = {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'text',
            'text': {'body': message}
        }
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=timeout)
        try:
            resp.raise_for_status()
        except Exception:
            current_app.logger.exception("WhatsApp send failed: %s", resp.text)
            raise
        return resp.json()



def verify_whatsapp_signature(raw_body: bytes, signature_header: str, app_secret: str) -> bool:
    if not signature_header or not app_secret:
        return False
    prefix = 'sha256='
    if not signature_header.startswith(prefix):
        return False
    sig_hex = signature_header[len(prefix):]
    mac = hmac.new(app_secret.encode('utf-8'), msg=raw_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig_hex)


