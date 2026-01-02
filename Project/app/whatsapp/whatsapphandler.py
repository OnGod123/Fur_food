import uuid
import hmac
import hashlib


from functools import wraps
from flask import Blueprint, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.whatsapp.utils.session import load_session, save_session, clear_session
from app.whatsapp.utils import format_summary
from app.orders.validator import validate_items
from app.whatsapp.utils.orders import build_order
from app.utils.pay_vendors_utils_utils import process_vendor_payout
from app.whatsapp.utils.paymnet_link import build_payment_link
from app.websocket.vendor_notify import notify_vendor_new_order
from app.whatsapp.utils.delivery import create_delivery, redirect_to_delivery
from app.delivery.redirect import redirect_to_bargain
from app.whatsapp.utils.ai.ai_step_guard.py import ai_guard_step
from app.Database.vendors_model import Vendor
from app.Database.user_models import User
from app.extensions import emit_to_room





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
        self.state = self.session.get("state", "MENU")

    def send(self, msg):
        self.whatsapp.send_text(self.phone, msg)



    def run(self):
        phone = self.phone
        text = self.text.strip()
        session_data = self.session
        state = self.state

    # ---------- MENU ----------
        if state == "MENU":
            result = ai_guard_step(
            step="MENU",
            user_input=text,
            expected="Choose one of: ORDER, WALLET, TRACK, ERRAND, RIDE",
            examples=[
                "Order food",
                "Fund wallet",
                "Track my delivery",
                "Send an errand",
                "Request a ride",
            ],
        )

            if not result["ok"]:
                self.send(result["hint"] + "\n\n" + MENU_TEXT)
                return "", 200

                cmd = result["value"]

            if cmd == "ORDER":
                session_data["state"] = "ASK_VENDOR"
                self.save()
                self.send("➡️ Enter vendor name (Example: `Jamborine`)")
                return "", 200

            if cmd == "WALLET":
                self.send(f"💰 Fund wallet:\n{build_payment_link(phone)}")
                return "", 200

            if cmd == "TRACK":
                session_data["state"] = "TRACK"
                self.save()
                self.send("➡️ Send delivery ID to track")
                return "", 200

            if cmd == "ERRAND":
                session_data["state"] = "ASK_ERRAND"
                self.save()
                self.send(Phone " Describe the errand properly")
                return "", 200

            if cmd == "RIDE":
                session_data["state"] = "ASK_RIDE"
                self.save()
                self.send(Phone, "Enter pickup location and destination \n login to negitiate the Tf-price")
                return "", 200

                self.send(Phone, MENU_TEXT)
                return "", 200

    # ---------- TRACK ----------
            if state == "TRACK":
                result = ai_guard_step(
                step="TRACK",
                user_input=text,
                expected="Send the delivery or tracking ID you received",
                examples=["DEL-102938", "ORDER-8891", "123456"],
                )
            if not result["ok"]:
                self.send(Phone,result["hint"])
                return "", 200

            tracking_id = result["value"]
            buyer_username = session_data.get("username")
            vendor_username = resolve_vendor_username(tracking_id)
            self.send(redirect_to_bargain(buyer_username, vendor_username))
            session_data["state"] = "MENU"
            self.save()
            return "", 200

    # ---------- ASK_VENDOR ----------
            if state == "ASK_VENDOR":
                result = ai_guard_step(
                step="ASK_VENDOR",
                user_input=text,
                expected="Enter the name of the food vendor",
                examples=["Jamborine", "Chicken Republic", "Mr Biggs"],
                )
            if not result["ok"]:
                self.send(Phone, result["hint"])
                return "", 200

            vendor_name = result["value"]
            with session_scope() as db:
            vendor = db.query(Vendor).filter(Vendor.name.ilike(f"%{vendor_name}%")).first()
            if not vendor:
                self.send("❌ Vendor not found. Try again.")
                return "", 200
            items = db.query(FoodItem).filter(FoodItem.vendor_id == vendor.id).limit(10).all()

            menu_map = {}
            menu_lines = []
            for idx, item in enumerate(items, start=1):
                menu_lines.append(f"{idx}) {item.name} — ₦{item.price}")
                menu_map[str(idx)] = {"id": item.id, "name": item.name, "price": item.price}

            session_data.update({
                "state": "ASK_ITEMS" if items else "ASK_CUSTOM_ITEM",
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "items_menu": menu_map if items else {},
                })
            self.save()

            if menu_lines:
                self.send(Phone,
                    "➡️ *What would you like to buy?*\n\n"
                    + "\n".join(menu_lines)
                    + "\n\nReply with:\n"
                    "• Item number (e.g. `1`)\n"
                    "• OR describe what you want if not listed"
                )
            else:
                self.send(Phone,
                "➡️ Vendor has no menu. Please describe what you want to buy.\n"
                "📝 *Example:* `Fufu – 2 wraps with egusi soup`"
                )
            return "", 200

    # ---------- ASK_CUSTOM_ITEM ----------
            if state == "ASK_CUSTOM_ITEM":
                result = ai_guard_step(
                step="ASK_CUSTOM_ITEM",
                user_input=text,
                expected="Describe the item clearly for the vendor",
                examples=["Fufu – 2 wraps with egusi soup"],
        )
            if not result["ok"]:
                self.send(result["hint"])
                return "", 200

            description = result["value"]
            ws.emit(
                    "custom_order_request",
                {"customer_phone": phone, "vendor_id": session_data["vendor_id"], "description": description},
                room=f"vendor_{session_data['vendor_id']}",
                )
            self.send("✅ Your request has been sent to the vendor. They will reply with price confirmation.")
            session_data["state"] = "MENU"
            self.save()
            return "", 200

    # ---------- ASK_ITEMS ----------
            if state == "ASK_ITEMS":
                menu = session_data.get("items_menu", {})
            if text.isdigit() and text in menu:
                item = menu[text]
                session_data.update({
                    "state": "ASK_ADDRESS",
                    "items": [{"id": item["id"], "name": item["name"], "price": item["price"], "qty": 1}],
                    })
                self.save()
                self.send("➡️ Send delivery address")
                return "", 200

        # Custom request to vendor
            with session_scope() as db:
                vendor = db.query(Vendor).get(session_data["vendor_id"])
            if vendor and vendor.whatsapp_phone:
                self.whatsapp.send_text(vendor.whatsapp_phone, f"📩 <adamu> Custom Order Request\nCustomer: {phone}\n{text}")
                self.send("📝 Request sent to vendor. They will contact you to confirm price.")
                session_data["state"] = "MENU"
                self.save()
                return "", 200

    # ---------- ASK_ADDRESS ----------
            if state == "ASK_ADDRESS":
                result = ai_guard_step(
                step="ASK_ADDRESS",
                user_input=text,
                expected="Provide full delivery address",
                examples=["No 10 Allen Avenue, Ikeja, Lagos"],
            )
            if not result["ok"]:
                self.send(Phone, result["hint"])
                return "", 200

            session_data["address"] = result["value"]
            session_data["total"] = sum(i["qty"] * i["price"] for i in session_data["items"])
            session_data["state"] = "CONFIRM"
            self.save()
            self.send(format_summary(session_data) + "\n➡️ Reply YES to confirm")
            return "", 200

    # ---------- CONFIRM ----------
            if state == "CONFIRM":
                result = ai_guard_step(
                step="CONFIRM",
                user_input=text,
                expected="Confirm your order with YES",
                examples=["YES", "Y"],
            )
            if not result["ok"] or result["value"].lower() not in ("yes", "y"):
                session_data["state"] = "MENU"
                self.save()
                self.send("❌ Order cancelled.")
                return "", 200

            with session_scope() as db:
                user = db.query(User).filter(User.whatsapp_phone == phone).first()
                vendor = db.query(Vendor).get(session_data["vendor_id"])
            if not user:
                user = User(id=str(uuid.uuid4()), whatsapp_phone=phone, wallet_balance=0)
                db.add(user)

            order = build_order(
                user_id=user.id,
                vendor_id=session_data["vendor_id"],
                items=session_data["items"],
                address=session_data["address"],
                phone=phone,
            )
            try:
                process_vendor_payout(user_id=user.id, vendor=vendor, vendor_id=vendor.id, order_id=order.id, amount=order.total, provider="paystack")
            except Exception:
                self.send("⚠️ Order created but payment processing failed. Support notified.")
            raise

            notify_vendor_new_order(order.id)
            ws.emit("vendor_new_order_details", order.to_dict(), room=f"vendor_{session_data['vendor_id']}")
            delivery = create_delivery(order)
            redirect_to_bargain(delivery.id)

            self.send("✅ Order placed. Rider is being assigned.")
            session_data["state"] = "MENU"
            self.save()
            return "", 200

    # ---------- ERRAND ----------
        if state == "ASK_ERRAND":
            result = ai_guard_step(
            step="ASK_ERRAND",
            user_input=text,
            expected="Describe the errand clearly, include pickup and destination",
            examples=[
                "Pick up documents from Ikeja and deliver to Lekki",
                "Buy groceries from Shoprite Yaba and deliver to my home",
                ],
            )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

            errand_text = result["value"]

        # Extract destination (after 'to')
        destination = None
        if " to " in errand_text.lower():
            destination = errand_text.lower().split(" to ")[-1].strip()

        # Emit errand to riders room
            ws.emit("new_errand", {"phone": phone, "task": errand_text}, room="riders")

        # Send to riders based on destination
            with session_scope() as db:
                from app.Database.RiderAndStrawler import  RiderAndStrawler as Rider
                query = db.query(Rider).filter(Rider.available == True)
            if destination:
                query = query.filter(Rider.destination.ilike(f"%{destination}%"))
            riders = query.limit(10).all()

            if riders:
                for rider in riders:
                    if rider.whatsapp_phone:
                        self.whatsapp.send_text(
                            rider.whatsapp_phone,
                         f"🚨 <adamu> New errand request!\nTask: {errand_text}\nCustomer: {phone}\n➡️ Login and message the user"
                        )
                        self.send(f"✅ Errand sent to {len(riders)} riders.")
            else:
                self.send("❌ No riders available for that destination at the moment.")

            session_data["state"] = "MENU"
            self.save()
            return "", 200

    # ---------- RIDE ----------
    if state == "ASK_RIDE":
        result = ai_guard_step(
            step="ASK_RIDE_PICKUP",
            user_input=text,
            expected="Enter your pickup location clearly",
            examples=["Ikeja Along Allen Avenue", "Shoprite Lekki Phase 1"],
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        session_data["pickup"] = result["value"]
        session_data["state"] = "ASK_RIDE_DESTINATION"
        self.save()
        self.send("➡️ Enter your destination")
        return "", 200

        if state == "ASK_RIDE_DESTINATION":
            result = ai_guard_step(
                step="ASK_RIDE_DESTINATION",
                user_input=text,
                expected="Enter your destination clearly",
                examples=["Lekki Phase 1", "Unilag Main Gate"],
            )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        session_data["destination"] = result["value"]
        with session_scope() as db:
            from app.Database.RiderAndStrawler import  RiderAndStrawler as Rider
            riders = db.query(Rider).filter(Rider.available == True).filter(Rider.destination.ilike(f"%{result['value']}%")).limit(10).all()

        if not riders:
            self.send("❌ No riders available for that destination at the moment.")
            session_data["state"] = "MENU"
            self.save()
            return "", 200

        for rider in riders:
            if rider.whatsapp_phone:
                self.whatsapp.send_text(
                    rider.whatsapp_phone,
                    f"🚗 <adamu> New ride request!\nPickup: {session_data['pickup']}\nDestination: {session_data['destination']}\nCustomer: {phone}\n➡️ Login and message the user"
                )

        self.send("✅ Ride request sent to available riders.")
        session_data["state"] = "MENU"
        self.save()
        return "", 200

    # ---------- FALLBACK ----------
    session_data["state"] = "MENU"
    self.save()
    self.send(Phone, MENU_TEXT)
    return "", 200

