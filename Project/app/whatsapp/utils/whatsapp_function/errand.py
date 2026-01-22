from app.whatsapp.utils.ai.ai_step_guard.py import ai_guard_step
from app.Database.user_models import User
from app.Database.errand import Errand
from app.Database.RiderAndStrawler import RiderAndStrawler
from app.extensions import session_scope, r
from app.handlers.sckoet.utils.city_database_utils.py import get_home_location,  find_nearby_vendors, find_nearby_rider

def errand():
    session = self.session
    text = self.text
    phone = self.phone
    state = session.get("state")

    # -------------------- ASK_ERRAND_PICKUP --------------------
    if state == "ASK_ERRAND_PICKUP":
        result = ai_guard_step(
            step="ASK_ERRAND_PICKUP",
            user_input=text,
            expected="Provide a real pickup location",
            examples=[
                "No 10 Allen Avenue, Ikeja, Lagos",
                "Shoprite Lekki Phase 1",
                "Unilag Main Gate, Akoka"
            ]
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        session["errand_pickup"] = result["value"]
        session["state"] = "ASK_ERRAND_DESTINATION"
        self.save()
        self.send("➡️ Got it! Now, where should this errand be delivered to?")
        return "", 200

    # -------------------- ASK_ERRAND_DESTINATION --------------------
    if state == "ASK_ERRAND_DESTINATION":
        result = ai_guard_step(
            step="ASK_ERRAND_DESTINATION",
            user_input=text,
            expected="Provide a real destination location",
            examples=[
                "No 12 Banana Island, Lagos",
                "Lekki Phase 1, Shoprite",
                "Ojota Bus Stop, Lagos"
            ]
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        session["errand_destination"] = result["value"]
        session["state"] = "CONFIRM_ERRAND"
        self.save()
        self.send(
            f"✅ Pickup: {session['errand_pickup']}\n"
            f"✅ Destination: {session['errand_destination']}\n\n"
            "Reply YES to confirm and proceed with payment."
        )
        return "", 200

    # -------------------- CONFIRM_ERRAND & PAYMENT --------------------
    if state == "CONFIRM_ERRAND":
        if text.strip().lower() not in ("yes", "y"):
            self.send("❌ Errand cancelled. Reply 'ERRAND' to start again.")
            session["state"] = "MENU"
            self.save()
            return "", 200

        pickup_address = session.get("errand_pickup")
        destination_address = session.get("errand_destination")
        errand_fare = 500  # example

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

            # Check if wallet has enough balance
            if wallet.balance < errand_fare:
                admin_account = current_app.config["ADMIN_PAYSTACK_ACCOUNT"]
                self.send(
                    f"💰 Insufficient wallet balance: ₦{wallet.balance}. "
                    f"Please pay ₦{errand_fare} to {admin_account} to proceed."
                )
                session["state"] = "AWAIT_ERRAND_PAYMENT"
                self.save()
                return "", 200

            # Debit wallet
            try:
                Wallet.debit(db, user.id, errand_fare)
            except Exception as e:
                self.send(f"⚠️ Could not debit wallet: {str(e)}")
                session["state"] = "MENU"
                self.save()
                return "", 200

            # Create errand
            home = get_home_location(phone)
            errand = Errand(
                user_id=user.id,
                description=f"Pickup from {pickup_address} → deliver to {destination_address}",
                pickup_address=pickup_address,
                pickup_latitude=home["lat"] if home else None,
                pickup_longitude=home["lng"] if home else None,
                destination_address=destination_address,
                status="PENDING",
                fare=errand_fare,
                created_at=datetime.utcnow()
            )
            db.add(errand)
            db.commit()
            session["errand_id"] = errand.id

            # Broadcast to nearby riders
            assigned_riders = []
            if home:
                nearby_riders = find_nearby_riders(home["lat"], home["lng"], radius_m=1500)
                for r in nearby_riders[:10]:
                    rider = db.query(RiderAndStrawler).filter_by(
                        id=r["rider_id"], is_verified=True, is_available=True
                    ).first()
                    if rider:
                        assigned_riders.append(rider)

            if not assigned_riders:
                self.send("⚠️ No available riders nearby. Try again later.")
            else:
                for rider in assigned_riders:
                    self.whatsapp.send_text(
                        rider.whatsapp_phone,
                        f"🚨 *New Errand Request!*\n\n"
                        f"🆔 Errand ID: {errand.id}\n"
                        f"📞 Customer: {phone}\n"
                        f"Pickup: {pickup_address}\n"
                        f"Destination: {destination_address}\n"
                        "Reply *ACCEPT* to take this errand."
                    )
                self.send(f"✅ Errand request broadcasted to {len(assigned_riders)} nearby riders.")

        session["state"] = "MENU"
        self.save()
        return "", 200

