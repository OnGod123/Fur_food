from datetime import datetime
from flask import current_app

from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step
from app.Database.user_models import User, Wallet
from app.Database.errand import Errand
from app.Database.RiderAndStrawler import RiderAndStrawler
from app.extensions import session_scope
from app.handlers.socket.utils.city_database_utils import (
    get_home_location,
    find_nearby_riders
)


def multiple_item_errand(self):
    session = self.session
    text = self.text
    phone = self.phone
    state = session.get("state")

    # -------------------- MULTIPLE_ORDER (ENTRY) --------------------
    if state == "MULTIPLE_ORDER":
        session.clear()
        session["state"] = "ASK_PURCHASE_LOCATION"
        self.save()

        self.send(
            "🧾 *Multiple Item Errand*\n\n"
            "Where should the rider buy these items from?"
        )
        return "", 200

    # -------------------- ASK_PURCHASE_LOCATION --------------------
    if state == "ASK_PURCHASE_LOCATION":
        result = ai_guard_step(
            step="ASK_PURCHASE_LOCATION",
            user_input=text,
            expected="Provide a real purchase location",
            examples=[
                "Kingstore Ikeja",
                "Swiss Way Supermarket Lekki",
                "Balogun Market Lagos"
            ]
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        session["purchase_location"] = result["value"]
        session["state"] = "ASK_DELIVERY_LOCATION"
        self.save()

        self.send("📍 Where should the items be delivered to?")
        return "", 200

    # -------------------- ASK_DELIVERY_LOCATION --------------------
    if state == "ASK_DELIVERY_LOCATION":
        result = ai_guard_step(
            step="ASK_DELIVERY_LOCATION",
            user_input=text,
            expected="Provide a real delivery location",
            examples=[
                "No 12 Banana Island, Lagos",
                "Ojota Bus Stop",
                "Lekki Phase 1"
            ]
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        session["delivery_location"] = result["value"]
        session["errand_items"] = []
        session["state"] = "ADD_ERRAND_ITEM"
        self.save()

        self.send(
            "🛒 Send items one by one.\n\n"
            "Type items naturally like:\n"
            "`Buy me sardine 2000`\n"
            "`bread 1200`\n"
            "`chocolate cake 2500`\n\n"
            "Send *DONE* when finished."
        )
        return "", 200

    # -------------------- ADD_ERRAND_ITEM --------------------
    if state == "ADD_ERRAND_ITEM":
        if text.strip().lower() in ("done", "finish"):
            if not session["errand_items"]:
                self.send("❌ You must add at least one item.")
                return "", 200

            total_items = sum(i["price"] for i in session["errand_items"])

            summary = "\n".join(
                f"- {i['item']} ₦{i['price']}"
                for i in session["errand_items"]
            )

            session["state"] = "CONFIRM_ERRAND"
            self.save()

            self.send(
                f"🧾 *Order Summary*\n\n"
                f"🛍 Buy From: {session['purchase_location']}\n"
                f"📦 Deliver To: {session['delivery_location']}\n\n"
                f"{summary}\n\n"
                f"💰 Items Total: ₦{total_items}\n"
                "Reply YES to confirm."
            )
            return "", 200

        # -------------------- PARSE ITEM NATURALLY --------------------
        result = ai_guard_step(
            step="ADD_ERRAND_ITEM",
            user_input=text,
            expected="Provide item name and price in Naira",
            examples=[
                "Buy me sardine 2000",
                "milk 1500",
                "bread 1200"
            ]
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        parsed = result["value"]

        try:
            # Extract item and price
            item_name = parsed.get("item") or parsed.get("name")
            item_price = int(parsed["price"])
            if item_price <= 0:
                raise ValueError("Price must be positive")
            if not item_name:
                raise ValueError("Item name cannot be empty")
        except Exception:
            self.send(
                "❌ Invalid format. Send each item like:\n"
                "`Buy me sardine 2000` or `bread 1200`\n"
                "Price is always assumed to be in Naira."
            )
            return "", 200

        session["errand_items"].append({
            "item": item_name,
            "place": session.get("purchase_location"),
            "price": item_price
        })

        self.save()
        self.send("✅ Item added. Send another item or DONE.")
        return "", 200

    # -------------------- CONFIRM_ERRAND & PAYMENT --------------------
    if state == "CONFIRM_ERRAND":
        if text.strip().lower() not in ("yes", "y"):
            self.send("❌ Errand cancelled.")
            session.clear()
            session["state"] = "MENU"
            self.save()
            return "", 200

        items = session["errand_items"]
        items_total = sum(i["price"] for i in items)
        service_fee = 500
        total_cost = items_total + service_fee

        with session_scope() as db:
            user = db.query(User).filter_by(whatsapp_phone=phone).first()
            if not user:
                self.send("❌ User not found.")
                session["state"] = "MENU"
                self.save()
                return "", 200

            wallet = db.query(Wallet).filter_by(user_id=user.id).with_for_update().first()
            if not wallet:
                self.send("❌ Wallet not found.")
                session["state"] = "MENU"
                self.save()
                return "", 200

            if wallet.balance < total_cost:
                admin_account = current_app.config["ADMIN_PAYSTACK_ACCOUNT"]
                self.send(
                    f"💰 *Insufficient Wallet Balance*\n\n"
                    f"Balance: ₦{wallet.balance}\n"
                    f"Required: ₦{total_cost}\n\n"
                    f"Send ₦{total_cost - wallet.balance} to:\n"
                    f"{admin_account}"
                )
                session["state"] = "AWAIT_ERRAND_PAYMENT"
                self.save()
                return "", 200

            Wallet.debit(db, user.id, total_cost)

            description = "; ".join(
                f"{i['item']} (₦{i['price']})"
                for i in items
            )

            home = get_home_location(phone)

            errand = Errand(
                user_id=user.id,
                description=description,
                pickup_address=session["purchase_location"],
                destination_address=session["delivery_location"],
                fare=total_cost,
                status="PENDING",
                created_at=datetime.utcnow()
            )
            db.add(errand)
            db.commit()

            if home:
                nearby = find_nearby_riders(home["lat"], home["lng"], radius_m=1500)
                for r in nearby[:10]:
                    rider = db.query(RiderAndStrawler).filter_by(
                        id=r["rider_id"],
                        is_verified=True,
                        is_available=True
                    ).first()
                    if rider:
                        self.whatsapp.send_text(
                            rider.whatsapp_phone,
                            f"🚨 *New Multiple Item Errand*\n\n"
                            f"🆔 {errand.id}\n"
                            f"🛍 Buy From: {session['purchase_location']}\n"
                            f"📦 Deliver To: {session['delivery_location']}\n\n"
                            + "\n".join(
                                f"- {i['item']} ₦{i['price']}"
                                for i in items
                            ) +
                            "\n\nReply *ACCEPT* to take this errand."
                        )

            self.send("✅ Errand sent to nearby riders.")

        session.clear()
        session["state"] = "MENU"
        self.save()
        return "", 200

