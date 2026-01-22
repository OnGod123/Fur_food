from app.Database.order_ride import  Ride_Order
from app.whatsapp.utils.ai.ai_step_guard  import ai_guard_step
from app.Database.user_models import User
from app.extensions import session_scope, r
from app.utils.bank.payvendor_rider import pay_vendor_or_rider
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step
from app.Database.user_models import User
from app.extensions import session_scope, r
from app.handlers.socket.utils.city_database_utils import get_home_location,  find_nearby_vendors, find_nearby_rider
from app.Database.RiderAndStrawler import RiderAndStrawler 

def confirm_ride(self):
    """
    Confirms and processes a ride booking.
    Precondition: session['state'] must be 'CONFIRM_RIDE'.
    Only changes state when moving forward or handling cancellation/errors.
    """

    session = self.session
    text = self.text.strip()
    phone = self.phone
    state = session.get("state")

    # Only proceed if state is CONFIRM_RIDE
    if state == "CONFIRM_RIDE":

        # ❌ User cancels
        if text.lower() not in ("yes", "y"):
            self.send("❌ Ride booking cancelled. Reply 'RIDE' to start again.")
            session["state"] = "MENU"
            self.save()
            return "", 200

        pickup_address = session.get("ride_pickup")
        destination_address = session.get("ride_destination")
        ride_fare = 500  # Example fixed fare

        with session_scope() as db:
            # Get user
            user = db.query(User).filter_by(whatsapp_phone=phone).first()
            if not user:
                self.send("❌ User not found.")
                session["state"] = "MENU"
                self.save()
                return "", 200

            # Check wallet
            wallet = db.query(Wallet).filter_by(user_id=user.id).with_for_update().first()
            if not wallet:
                self.send("❌ Wallet not found.")
                session["state"] = "MENU"
                self.save()
                return "", 200

            if wallet.balance < ride_fare:
                admin_account = current_app.config["ADMIN_PAYSTACK_ACCOUNT"]
                self.send(
                    f"💰 Insufficient wallet balance: ₦{wallet.balance}. "
                    f"Please pay ₦{ride_fare} to {admin_account} to proceed."
                )
                session["state"] = "AWAIT_RIDE_PAYMENT"
                self.save()
                return "", 200

            # Debit wallet
            try:
                Wallet.debit(db, user.id, ride_fare)
            except Exception as e:
                self.send(f"⚠️ Could not debit wallet: {str(e)}")
                session["state"] = "MENU"
                self.save()
                return "", 200

            # Create ride order
            home = get_home_location(phone)
            ride_order = RideOrder(
                user_id=user.id,
                pickup_address=pickup_address,
                pickup_latitude=home["lat"] if home else None,
                pickup_longitude=home["lng"] if home else None,
                destination_address=destination_address,
                status="PENDING",
                fare=ride_fare,
                created_at=datetime.utcnow()
            )
            db.add(ride_order)
            db.commit()
            session["ride_order_id"] = ride_order.id

            # Broadcast to nearby verified riders
            assigned_riders = []
            if home:
                nearby_riders = find_nearby_riders("LAGOS", home["lat"], home["lng"], radius_m=1500)
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
                        f"🚨 *New Ride Request!*\n\n"
                        f"🆔 Ride ID: {ride_order.id}\n"
                        f"📞 Customer: {phone}\n"
                        f"Pickup: {pickup_address}\n"
                        f"Destination: {destination_address}\n"
                        "Reply *ACCEPT* to take this ride."
                    )
                self.send(f"✅ Ride request broadcasted to {len(assigned_riders)} nearby riders.")

        # Move user back to main menu after success
        session["state"] = "MENU"
        self.save()

    return "", 200

