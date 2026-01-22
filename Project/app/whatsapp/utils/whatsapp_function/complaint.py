from app.utils.bank.payvendor_rider import pay_vendor_or_rider
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step
from app.Database.user_models import User
from app.Database.vendors_model import Vendor
from app.Database.Accept_errand import ErrandAcceptance
from app.Database.Accept_ride import RideAcceptance
from app.extensions import session_scope, r
from app.handlers.socket.utils.city_database_utils import get_home_location,  find_nearby_vendors, find_nearby_rider
from app.Database.delivery import Delivery

def complaint(self):
    session = self.session
    text = self.text.strip()
    phone = self.phone
    state = session.get("state")

    # ---------- ASK_COMPLAINT_TYPE ----------
    if state == "ASK_COMPLAINT_TYPE":
        result = ai_guard_step(
            step="COMPLAINT_TYPE_SELECTION",
            user_input=text,
            expected="Enter the type of complaint: ride, errand, or food",
            examples=["ride", "errand", "food"]
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        complaint_type = result["value"].lower()
        if complaint_type not in ["ride", "errand", "food"]:
            self.send("❌ Invalid type. Reply with 'ride', 'errand', or 'food'.")
            return "", 200

        session["complaint_type"] = complaint_type
        session["state"] = "COMPLAINT"
        self.save()

        # Automatically fetch the latest ID for the complaint type
        user_id = session.get("user_id")
        if not user_id:
            self.send("❌ Could not identify your account. Please log in again.")
            session["state"] = "MENU"
            self.save()
            return "", 200

        with session_scope() as db:
            if complaint_type == "food":
                latest_delivery = db.query(Delivery)\
                    .filter_by(user_id=user_id)\
                    .order_by(Delivery.created_at.desc()).first()
                if not latest_delivery:
                    self.send("❌ No food deliveries found for your account.")
                    session["state"] = "MENU"
                    self.save()
                    return "", 200
                session["complaint_id"] = latest_delivery.id
                self.send(f"➡️ Your latest food delivery ID is {latest_delivery.id}. Describe your complaint:")

            elif complaint_type == "ride":
                latest_ride = db.query(RideAcceptance)\
                    .filter_by(customer_phone=phone)\
                    .order_by(RideAcceptance.accepted_at.desc()).first()
                if not latest_ride:
                    self.send("❌ No rides found for your account.")
                    session["state"] = "MENU"
                    self.save()
                    return "", 200
                session["complaint_id"] = latest_ride.ride_id
                self.send(f"➡️ Your latest ride ID is {latest_ride.ride_id}. Describe your complaint:")

            elif complaint_type == "errand":
                latest_errand = db.query(ErrandAcceptance)\
                    .filter_by(customer_phone=phone)\
                    .order_by(ErrandAcceptance.accepted_at.desc()).first()
                if not latest_errand:
                    self.send("❌ No errands found for your account.")
                    session["state"] = "MENU"
                    self.save()
                    return "", 200
                session["complaint_id"] = latest_errand.errand_id
                self.send(f"➡️ Your latest errand ID is {latest_errand.errand_id}. Describe your complaint:")

        return "", 200

    # ---------- COMPLAINT ----------
    if state == "COMPLAINT":
        complaint_text = text
        if not complaint_text:
            self.send("❌ Please describe your complaint clearly.")
            return "", 200

        session["last_complaint"] = complaint_text
        complaint_type = session.get("complaint_type")
        complaint_id = session.get("complaint_id")
        self.save()

        with session_scope() as db:
            info_sent = False

            if complaint_type == "food":
                delivery = db.query(Delivery).filter_by(id=complaint_id).first()
                if delivery:
                    vendor = db.query(Vendor)\
                        .filter_by(id=delivery.order_single.vendor_id).first() if delivery.order_single else None
                    rider = db.query(RiderAndStrawler)\
                        .filter_by(id=delivery.rider_id).first() if delivery.rider_id else None
                    self.send(
                        f"📌 Complaint registered for Delivery {complaint_id}.\n"
                        f"Vendor: {vendor.business_name if vendor else 'Unknown'}\n"
                        f"Vendor Phone: {vendor.business_phone if vendor else 'Unknown'}\n"
                        f"Rider Phone: {rider.whatsapp_phone if rider else 'Unknown'}"
                    )
                    info_sent = True

            elif complaint_type == "ride":
                ride_acceptance = db.query(RideAcceptance).filter_by(ride_id=complaint_id).first()
                if ride_acceptance:
                    rider = db.query(RiderAndStrawler).filter_by(id=ride_acceptance.rider_id).first()
                    self.send(
                        f"📌 Complaint registered for Ride {complaint_id}.\n"
                        f"Rider Phone: {rider.whatsapp_phone if rider else 'Unknown'}"
                    )
                    info_sent = True

            elif complaint_type == "errand":
                errand_acceptance = db.query(ErrandAcceptance).filter_by(errand_id=complaint_id).first()
                if errand_acceptance:
                    rider = db.query(RiderAndStrawler).filter_by(id=errand_acceptance.rider_id).first()
                    self.send(
                        f"📌 Complaint registered for Errand {complaint_id}.\n"
                        f"Rider Phone: {rider.whatsapp_phone if rider else 'Unknown'}"
                    )
                    info_sent = True

            if not info_sent:
                self.send("❌ Could not find associated vendor/rider. Complaint logged for admin review.")

            # Optional: save complaint to DB
            # db.add(Complaint(user_id=user_id, type=complaint_type, target_id=complaint_id, text=complaint_text))
            # db.commit()

        session["state"] = "MENU"
        self.save()
        return "", 200

