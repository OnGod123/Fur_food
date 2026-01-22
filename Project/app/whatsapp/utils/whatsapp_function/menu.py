from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step

def menu(self):
    session = self.session
    text = self.text.strip()
    state = session.get("state")

    if state == "MENU":
    
        result = ai_guard_step(
        step="MENU",
        user_input=text,
        expected="Choose a menu option",
        examples=[
            "1", "Order food",
            "2", "Fund wallet",
            "3", "View orders",
            "4", "Ride",
            "5", "Send errand",
            "6", "Track",
            "7", "Complaint",
            "8", "Accept ride",
            "9", "Rider nearby",
            "10", "Errand agent nearby",
            "11", "Load wallet",
        ],
        )

        if not result["ok"]:
            self.send(
                "🏠 *CampusRide Menu*\n\n"
                "1️⃣ Order food\n"
                "2️⃣ Fund wallet\n"
                "3️⃣ View orders\n"
                "4️⃣ Ride\n"
                "5️⃣ Send errand\n"
                "6️⃣ Track\n"
                "7️⃣ Complaint\n"
                "8️⃣ Accept ride\n"
                "9️⃣ Rider nearby\n"
                "🔟 Errand agent nearby\n"
                "1️⃣1️⃣ Load wallet\n"
            )
            return "", 200

        choice = result["value"]

        # -------- MENU → STATE MAPPING --------
        if choice in ("1", "order food"):
            session["state"] = "ORDER"

        elif choice in ("2", "fund wallet", "11", "load wallet"):
            session["state"] = "WALLET"

        elif choice in ("3", "view orders"):
            session["state"] = "TRACK"

        elif choice in ("4", "ride"):
            session["state"] = "ASK_RIDE_PICKUP"

        elif choice in ("5", "send errand"):
            session["state"] = "ASK_ERRAND"

        elif choice in ("6", "track"):
            session["state"] = "TRACK"

        elif choice in ("7", "complaint"):
            session["state"] = "ASK_COMPLAINT_TYPE"

        elif choice in ("8", "accept ride"):
            session["state"] = "ACCEPT_RIDE"

        elif choice in ("9", "rider nearby"):
            session["state"] = "FIND_NEARBY_RIDER"

        elif choice in ("10", "errand agent nearby"):
            session["state"] = "FIND_NEARBY_ERRAND_AGENT"
        
        elif choice in ("11", "order_multiple_items"):
            session["state"] == "MULTIPLE_ORDER"

        self.save()
        return "", 200

