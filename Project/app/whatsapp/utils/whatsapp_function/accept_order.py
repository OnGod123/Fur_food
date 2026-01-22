from app.utils.bank. payvendor_rider import pay_vendor_or_rider
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step
from app.Database.user_models import User
from app.Database.vendors_model import Vendor
from app.Database.Accept_errand import ErrandAcceptance
from app.Database.Accept_ride import RideAcceptance 
from app.extensions import session_scope


def handle_accept_order(self, phone, session, text):
    state = session.get("state")
    text_clean = text.strip().lower()

    # -------------------- Step 1: Select order type --------------------
    if state == "ACCEPT_ORDER":
        result = ai_guard_step(
            step="ACCEPT_ORDER",
            user_input=text_clean,
            expected="Enter type: ride, errand, or food",
            examples=["ride", "errand", "food"]
        )
        if not result["ok"]:
            self.send(phone, result["hint"])
            return

        order_type = result["value"].lower()
        session["accept_type"] = order_type
        session["state"] = "ASK_ACCEPT_ID"
        self.save_session(phone, session)
        self.send(phone, f"➡️ Enter the {order_type} ID you want to accept:")
        return

    # -------------------- Step 2: Accept order ID --------------------
    if state == "ASK_ACCEPT_ID":
        if not text_clean.isdigit():
            self.send(phone, "❌ Provide numeric ID only.")
            return

        order_id = int(text_clean)
        order_type = session.get("accept_type")

        with session_scope() as db:
            # ✅ Fetch verified & available rider
            rider = db.query(RiderAndStrawler).filter_by(
                whatsapp_phone=phone, is_verified=True, is_available=True
            ).first()
            if not rider:
                self.send(phone, "❌ Only verified & available riders can accept orders.")
                session["state"] = "MENU"
                self.save_session(phone, session)
                return

            # -------------------- ACCEPT RIDE --------------------
            if order_type == "ride":
                ride = db.query(RideOrder).filter_by(id=order_id).first()
                if not ride:
                    self.send(phone, f"❌ Ride {order_id} not found.")
                    return

                existing = db.query(RideAcceptance).filter_by(ride_id=ride.id).first()
                if existing:
                    self.send(phone, f"❌ Ride {order_id} already accepted.")
                    return
                    acceptance = RideAcceptance(
                    ride_id=ride.id,
                    rider_id=rider.id,
                    rider_phone=rider.whatsapp_phone,
                    customer_phone=ride.customer_phone,
                    pickup=ride.pickup,
                    destination=ride.destination,
                    accepted_at=datetime.utcnow()
                )
                db.add(acceptance)
                db.commit()

                try:
                    pay_vendor_or_rider("rider", rider.id, ride.fare, f"Payment for ride {ride.id}")
                except Exception as e:
                    self.send(phone, f"⚠️ Ride accepted but payment failed: {str(e)}")
                    session["state"] = "MENU"
                    self.save_session(phone, session)
                    return

                self.send(phone, f"✅ Ride {ride.id} accepted. Payment ₦{ride.fare}")

            # -------------------- ACCEPT ERRAND --------------------
            elif order_type == "errand":
                errand = db.query(Errand).filter_by(id=order_id).first()
                if not errand:
                    self.send(phone, f"❌ Errand {order_id} not found.")
                    return

                existing = db.query(ErrandAcceptance).filter_by(errand_id=errand.id).first()
                if existing:
                    self.send(phone, f"❌ Errand {order_id} already accepted.")
                    return

                acceptance = ErrandAcceptance(
                    errand_id=errand.id,
                    rider_id=rider.id,
                    rider_phone=rider.whatsapp_phone,
                    customer_phone=errand.user.whatsapp_phone,
                    pickup_address=errand.pickup_address,
                    destination_address=errand.destination_address,
                    accepted_at=datetime.utcnow()
                )
                db.add(acceptance)
                db.commit()

                try:
                    pay_vendor_or_rider("rider", rider.id, errand.fare, f"Payment for errand {errand.id}")
                except Exception as e:
                    self.send(phone, f"⚠️ Errand accepted but payment failed: {str(e)}")
                    session["state"] = "MENU"
                    self.save_session(phone, session)
                    return

                self.send(phone, f"✅ Errand {errand.id} accepted. Payment ₦{errand.fare}")

            # -------------------- ACCEPT FOOD DELIVERY --------------------
            elif order_type == "food":
                delivery = db.query(Delivery).filter_by(id=order_id).first()
                if not delivery:
                    self.send(phone, f"❌ Delivery {order_id} not found.")
                    return

                if delivery.rider_id:
                    self.send(phone, f"❌ Delivery {order_id} has already been accepted.")
                    return

                delivery.rider_id = rider.id
                delivery.status = "accepted"
                db.add(delivery)
                db.commit()

                delivery_fee = delivery.delivery_fee or 500
                try:
                    pay_vendor_or_rider("rider", rider.id, delivery_fee, f"Payment for delivery {delivery.id}")
                except Exception as e:
                    self.send(phone, f"⚠️ Delivery accepted but payment failed: {str(e)}")
                    session["state"] = "MENU"
                    self.save_session(phone, session)
                    return

                self.send(phone, f"✅ Delivery {delivery.id} accepted. Payment ₦{delivery_fee}")

        # -------------------- Finalize --------------------
        session["state"] = "MENU"
        self.save_session(phone, session)
        return

