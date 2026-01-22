import uuid
import hmac
import hashlib
from functools import wraps
from flask import Blueprint, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.whatsapp.utils.load_session import load_session, save_session
from app.whatsapp.utils import format_summary
from app.whatsapp.utils.orders import build_order
from app.utils.pay_vendors_utils.engine import process_vendor_payout
from app.whatsapp.utils.payment_link import build_payment_link
from app.whatsapp.utils.notify_vendor import notify_vendor_new_order
from app.whatsapp.utils.delivery import create_delivery, redirect_to_delivery
from app.whatsapp.utils.track_utils import redirect_to_bargain
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step
from app.Database.vendors_model import Vendor
from app.Database.user_models import User
from app.extensions import emit_to_room
from app.whatsapp.utils.track_utils import resolve_vendor, resolve_buyer
from app.whatsapp.utils.whatsapp_function.select_vendor_name import select_vendor_by_name
from app.whatsapp.utils.whatsapp_function.show_vendor import show_vendor_menu
from app.whatsapp.utils.whatsapp_function.menu import menu
from app.whatsapp.utils.whatsapp_function.login import login
from app.whatsapp.utils.whatsapp_function.book_ride import book_ride
from app.whatsapp.utils.whatsapp_function.complaint import complaint
from app.whatsapp.utils.whatsapp_function.ask_address import ask_address
from app.whatsapp.utils.whatsapp_function.accept_order import  handle_accept_order
from app.whatsapp.utils.whatsapp_function.custom_item import  handle_custom_item
from app.whatsapp.utils.whatsapp_function.confirm_ride import confirm_ride 
from app.whatsapp.utils.whatsapp_function.payment import payment
from app.whatsapp.utils.whatsapp_function.find_rider_nearby import state_find_nearby_rider
from app.whatsapp.utils.whatsapp_function.find_nearby_errand import state_find_nearby_errand
from app.whatsapp.utils.whatsapp_function.order import order 
from app.whatsapp.utils.whatsapp_function.order import select_nearby_vendors

class WhatsAppClient:
    def __init__(self, token: str, phone_number_id: str, api_version: str):
        if not token or not phone_number_id:
            raise ValueError("WHATSAPP_TOKEN and META_PHONE_NUMBER_ID must be set")
        self.token = token
        self.phone_number_id = phone_number_id
        self.api_version = api_version
        self.text = text
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


class WhatsAppFlow:
    def __init__(self, phone, text, sender: WhatsAppClient):
        self.phone = phone
        self.text = text
        self.whatsapp = sender
        self.session = load_session(phone)
        self.save = save_session(self.phone, self.session)
        self.state = self.session.get("state")

    def send(self, msg):
        self.whatsapp.send_text(self.phone, msg)

    def run(self):
        phone = self.phone
        text = self.text.strip()
        session_data = self.session
        state = self.state
        if not session.get("registered") or not state:
          self.login()
        menu()
        handle_accept_order()
        ask_address()
        ask_item()
        book_ride()
        track_order()
        show_vendor_menu()
        select_vendor_by_name()
        payment()
        confirm_ride()
        order()
        login()
        errand()
        complaint()
        select_vendor_by_name()
        track_order()
        handle_custom_item()
        handle_accept_order(phone, session, text)
        state_find_nearby_rider(session, text, phone, order_fare, order_type="ride")
        state_find_nearby_errand(session, text, phone, order_fare, order_type="errand")
        select_nearby_vendors(session, phone)







