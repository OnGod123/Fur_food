from app.Database.vendors_model import Vendor
from app.extensions import session_scope, r
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step

def handle_custom_item():
    session = self.session
    text = self.text
    phone = self.phone
    state = session.get("state")

    if state == "CUSTOM_ITEM":

        result = ai_guard_step(
            step="CUSTOM_ITEM",
            user_input=text,
            expected="Describe the custom item you want to order clearly",
            examples=[
                "2 pieces of grilled chicken with fried rice",
                "Large pepper soup with extra spice",
                "1 large pizza with extra cheese and mushrooms"
            ],
        )

        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        description = result["value"]
        session["custom_item_description"] = description
        self.save()

        vendor_id = session.get("vendor_id")
        if not vendor_id:
            self.send("❌ Vendor not found. Please start your order again.")
            session["state"] = "MENU"
            self.save()
            return "", 200
        with session_scope() as db:
            vendor = db.query(Vendor).filter_by(id=vendor_id).first()
        if not vendor:
            self.send("❌ Vendor not found. Please start your order again.")
            session["state"] = "MENU"
            self.save()
            return "", 200
        self.whatsapp.send_text(
            vendor.business_phone,
            f"🆕 *Custom Order Request*\n\n"
            f"📞 Customer Phone: {phone}\n"
            f"🍴 Order Description: {description}\n\n"
            "The customer will be contacted shortly."
        )

        session["state"] = "MENU"
        self.save()
        self.send(
            "✅ Your custom order has been sent to the vendor.\n"
            "The vendor will contact you in a few minutes."
        )
        return "", 200

