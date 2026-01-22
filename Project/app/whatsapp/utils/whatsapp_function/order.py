from app.handlers.socket.utils.city_database_utils import get_home_location 
from app.extensions import session_scope, r
from app.Database.vendors_model import Vendor
from app.handlers.socket.utils.city_database_utils import get_home_location,  find_nearby_vendors, find_nearby_rider

def order():
    session = self.session
    text = self.text
    phone = self.phone
    state = session.get("state")

    # ---------- ORDER ENTRY ----------
    if state == "ORDER":
        session["state"] = "ORDER_METHOD"
        self.save()
        self.send(
            "🍽️ Order food selected!\n"
            "Choose an option:\n"
            "1️⃣ Vendors near me\n"
            "2️⃣ Select vendor by name"
        )
        return "", 200

    # ---------- ORDER METHOD ----------
    if state == "ORDER_METHOD":
        # 1️⃣ If user has already received nearby vendor list → validate selection
        if "select_vendor_step" in session:
            result = ai_guard_step(
                step="SELECT_VENDOR",
                user_input=text,
                expected="Reply with a number corresponding to a vendor",
                examples=list(session["select_vendor_step"].keys()),
            )
            if not result["ok"] or text not in session["select_vendor_step"]:
                self.send("❌ Invalid selection. Reply with a number from the list.")
                return "", 200

            selected = session["select_vendor_step"][text]
            session["vendor_id"] = selected["vendor_id"]
            session.pop("select_vendor_step", None)
            session["state"] = "SHOW_VENDOR_MENU"
            self.save()
            return "", 200

        # 2️⃣ First-time choice: Nearby or By Name
        result = ai_guard_step(
            step="ORDER_METHOD",
            user_input=text,
            expected="Reply with 1 or 2",
            examples=["1", "2"],
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        if result["value"] == "1":
            # Nearby vendors → query DB & build selection
            message = select_nearby_vendors(session, phone)
            self.save()
            self.send(message)
            return "", 200

        if result["value"] == "2":
            session["state"] = "ASK_VENDOR_BY_NAME"
            self.save()
            self.send("➡️ Enter the vendor name you want to order from:")
            return "", 200


def select_nearby_vendors(session, phone):
    loc = get_home_location(phone)
    if not loc:
        session["state"] = "MENU"
        return "❌ You have not set your home location. Please set it first."

    nearby_vendors = find_nearby_vendors("LAGOS", loc["lat"], loc["lng"], radius_m=1500)
    if not nearby_vendors:
        session["state"] = "MENU"
        return "❌ No vendors available nearby."

    with session_scope() as db:
        assigned_vendors = []
        for v in nearby_vendors:
            vendor = db.query(Vendor).filter_by(id=v["vendor_id"], is_verified=True).first()
            if vendor:
                assigned_vendors.append({
                    "vendor_id": vendor.id,
                    "name": vendor.business_name,
                    "phone": vendor.business_phone,
                    "distance": v["distance_m"],
                    "paystack_account": vendor.paystack_account
                })
            if len(assigned_vendors) >= 10:
                break

        if not assigned_vendors:
            session["state"] = "MENU"
            return "❌ No verified vendors available nearby."

        session["select_vendor_step"] = {str(i + 1): v for i, v in enumerate(assigned_vendors)}

        message = "🏪 Nearby vendors:\n\n"
        for i, v in enumerate(assigned_vendors, start=1):
            message += (
                f"{i}. {v['name']} | Vendor ID: {v['vendor_id']} | "
                f"Distance: {v['distance']} m | Paystack: {v['paystack_account']}\n"
            )
        message += "\nReply with the number (1–10) to select a vendor."
        return message

