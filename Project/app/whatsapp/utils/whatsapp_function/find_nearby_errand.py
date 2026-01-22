from app.utils.bank.payvendor_rider import pay_vendor_or_rider
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step
from app.Database.user_models import User
from app.Database.vendors_model import Vendor
from app.Database.Accept_errand import ErrandAcceptance
from app.Database.Accept_ride import RideAcceptance
from app.extensions import session_scope, r
from app.handlers.socket.utils.city_database_utils import get_home_location,  find_nearby_vendors, find_nearby_rider

def state_find_nearby_errand(session, text, phone, order_fare, order_type="errand"):
    """
    WhatsApp bot state: find nearby riders for errands, list top 10,
    AI Guard selects, check wallet/pay, pay rider.
    """
    state = session.get("state")
    if state == "NEARBY_ERRAND":

        step_description = session.get(
            "current_errand_description",
            "No errand description available. Please input errand details first."
        )

        # Step 0: Get user home location
        loc = get_home_location(phone)
        if not loc:
            session["state"] = "MENU"
            return f"❌ Could not find your home location. Please set it first.\n\nErrand details:\n{step_description}"

        nearby_riders = find_nearby_riders("LAGOS", loc["lat"], loc["lng"], radius_m=1500)
        if not nearby_riders:
            session["state"] = "MENU"
            return f"❌ No riders available nearby.\n\nErrand details:\n{step_description}"

        with session_scope() as db:
            # Step 1b: Resolve top 10 verified & available riders
            assigned_riders = []
        for r in nearby_riders:
            rider = db.query(RiderAndStrawler).filter_by(
                id=r["rider_id"], is_verified=True, is_available=True
            ).first()
            if rider:
                assigned_riders.append({
                    "rider_id": rider.id,
                    "name": rider.full_name,
                    "phone": rider.whatsapp_phone,
                    "distance": r["distance_m"],
                    "paystack_account": rider.paystack_account
                })
            if len(assigned_riders) >= 10:
                break

        if not assigned_riders:
            session["state"] = "MENU"
            return f"❌ No verified riders available nearby.\n\nErrand details:\n{step_description}"

        # Step 2: List riders if first time
        if "select_rider_step" not in session:
            session["select_rider_step"] = {str(i+1): r for i, r in enumerate(assigned_riders)}
            message = f"🚗 Nearby riders for your errand:\n\n{step_description}\n\n"
            for i, r in enumerate(assigned_riders, start=1):
                message += (
                    f"{i}. {r['name']} | Rider ID: {r['rider_id']} | "
                    f"Distance: {r['distance']} m | Paystack: {r['paystack_account']}\n"
                )
            message += "\nReply with the number (1-10) to select a rider."
            return message

        # Step 3: AI Guard for rider selection
        result = ai_guard_step(
            step="SELECT_RIDER",
            user_input=text,
            expected="Enter the number corresponding to the rider you want to select",
            examples=list(session["select_rider_step"].keys())
        )
        if not result["ok"]:
            return f"{result['hint']}\n\nErrand details:\n{step_description}"

        selection = result["value"].strip()
        if selection not in session["select_rider_step"]:
            return f"❌ Invalid selection. Reply with a number 1-10.\n\nErrand details:\n{step_description}"

        selected_rider = session["select_rider_step"][selection]

        # Step 4: Check user wallet before payment
        wallet = db.query(Wallet).filter_by(user_id=session.get("user_id")).first()
        if not wallet or wallet.balance < order_fare:
            session["state"] = "MENU"
            session.pop("select_rider_step", None)
            return f"❌ Insufficient wallet balance for ₦{order_fare}.\n\nErrand details:\n{step_description}"

        # Step 6: Make payment
        try:
            pay_vendor_or_rider(
                "rider",
                selected_rider["rider_id"],
                order_fare,
                f"Payment for {order_type} errand"
            )
            wallet.balance -= order_fare
            db.commit()
        except Exception as e:
            session["state"] = "MENU"
            session.pop("select_rider_step", None)
            return f"⚠️ Payment failed: {str(e)}\n\nErrand details:\n{step_description}"

    # Step 7: Success
        session["state"] = "MENU"
        session.pop("select_rider_step", None)
        return (
            f"✅ Rider {selected_rider['name']} ({selected_rider['phone']}) selected and paid ₦{order_fare}.\n\n"
            f"Errand details sent to rider:\n{step_description}"
        )

