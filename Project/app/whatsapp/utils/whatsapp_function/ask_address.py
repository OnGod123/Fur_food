from app.Database.delivery import Delivery
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step
from app.Database.user_models import User
from app.Database.vendors_model import Vendor
from app.extensions import session_scope

def ask_address(self):
    session = self.session
    text = self.text
    phone = self.phone
    state = session.get("state")

    if state == "ASK_ADDRESS":

    # 1️⃣ Validate address
        result = ai_guard_step(
            step="LOCATABLE_ADDRESS",
            user_input=text,
            expected="Provide a real, locatable address",
            examples=[
                "No 10 Allen Avenue, Ikeja, Lagos",
                "Shoprite Lekki Phase 1",
                "Unilag Main Gate, Akoka",
                "Ojota Bus Stop, Lagos",
            ],
        )

        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        delivery_address = result["value"]
        session["address"] = delivery_address
        self.save()

        with session_scope() as db:
        # 2️⃣ Get user
            user = db.query(User).filter_by(whatsapp_phone=phone).first()
            if not user:
                self.send("❌ User not found.")
                session["state"] = "MENU"
                self.save()
                return "", 200

        # 3️⃣ Get vendor
        vendor_id = session.get("vendor_id")
        vendor = db.query(Vendor).filter_by(id=vendor_id).first()

        if not vendor:
            self.send("❌ Vendor not found.")
            session["state"] = "MENU"
            self.save()
            return "", 200

        # 4️⃣ Item & total
        item = session.get("selected_item")
        qty = session.get("quantity", 1)
        total = item["price"] * qty

        # 5️⃣ Create order
        order = OrderSingle(
            user_id=user.id,
            item_data=item,
            total=total,
            vendor_id=vendor.id,
            vendor_name=vendor.business_name,
            product_name=item["name"],
            recipient_address=delivery_address,
        )
        delivery = Delivery(user_id=user.id, order_single_id = order.id, delivery_address = session["address"])
        db.add(order)
        db.flush()  # get order.id

        session["order_id"] = order.id

        # 6️⃣ Find rider home location
        home = get_home_location(phone)
        if not home:
            self.send("❌ Please set your home location first using *SET LOCATION*.")
            session["state"] = "MENU"
            db.commit()
            self.save()
            return "", 200

        # 7️⃣ Find nearby riders (geo only)
        nearby_riders = find_nearby_riders(
            "LAGOS",
            home["lat"],
            home["lng"],
            radius_m=TWELVE_FIELDS_M,
        )

        if not nearby_riders:
            self.send("❌ No riders available nearby.")
            session["state"] = "MENU"
            db.commit()
            self.save()
            return "", 200

        # 8️⃣ Resolve riders from DB (MAX 10)
        rider_ids = [r["rider_id"] for r in nearby_riders[:10]]

        riders = (
            db.query(Rider)
            .filter(Rider.id.in_(rider_ids), Rider.is_active == True)
            .all()
        )

        # 9️⃣ Broadcast order to riders
        for r in riders:
            message = (
                "🚴 *New Delivery Request*\n\n"
                f"🧾 Order ID: {order_id}\n\n"
                f"🏪 Pickup Vendor:\n"
                f"{vendor.business_name}\n"
                f"{vendor.business_address}\n\n"
                f"📦 Item: {item['name']} x{qty}\n"
                f"💰 Amount: ₦{total}\n\n"
                f"🏠 Drop-off Address:\n{delivery_address}\n\n"
                f"👤 Customer: {user.first_name}\n"
                f"📞 Phone: {phone}\n\n"
                "Reply *ACCEPT* to take this delivery."
            )

            self.whatsapp.send_text(r.phone, message)

        db.commit()

        # 🔟 Final user message
        session["state"] = "AWAIT_RIDER_ACCEPTANCE"
        self.save()

        self.send(
            "✅ Your order has been sent to nearby riders.\n"
            "You will be notified once a rider accepts."
        )
        return "", 200

