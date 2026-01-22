
from app.whatsapp.utils.track_utils import redirect_to_bargain, resolve_buyer
from app.whatsapp.utils.ai.guard_step_guard import ai_guard_step 

def track_order(self):
    session = self.session
    text = self.text
    phone = self.phone
    state = session.get("state")

    if state == "TRACk":
        result = ai_guard_step(
            step="TRACK",
            user_input=text,
            expected="Send the delivery or tracking ID you received",
            examples=["DEL-102938", "ORDER-8891", "123456"],
        )

        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        tracking_id = result["value"]
        buyer_username = session.get("username") or resolve_buyer(phone)
        vendor_username = resolve_vendor_username(tracking_id)
        self.send(redirect_to_bargain(buyer_username, vendor_username))
        session["state"] = "MENU"
        self.save()
        return "", 200

