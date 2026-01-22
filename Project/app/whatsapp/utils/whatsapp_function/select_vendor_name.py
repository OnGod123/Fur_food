from app.Database.vendors_model import Vendor
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step

def select_vendor_by_name():
    session = self.session
    text = self.text
    state = session.get("state")

    if state == "ASK_VENDOR_BY_NAME":

        result = ai_guard_step(
            step="ASK_VENDOR_BY_NAME",
            user_input=text,
            expected="Vendor name",
            examples=["Chicken Republic", "Boluid"],
            )

        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        with session_scope() as db:
            vendor = (
                db.query(Vendor)
                .filter(Vendor.business_name.ilike(f"%{result['value']}%"))
                .first()
            )

        if not vendor:
            self.send("❌ Vendor not found.")
            return "", 200

        session["vendor_id"] = vendor.id
        session["vendor_phone"] = vendor.phone
        session["state"] = "SHOW_VENDOR_MENU"
        self.save()
        return "", 200

