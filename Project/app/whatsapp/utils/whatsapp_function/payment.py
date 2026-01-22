from app.utils.bank.payvendor_rider import pay_vendor_or_rider
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step
from app.Database.user_models import User
from app.Database.vendors_model import Vendor
from app.extensions import session_scope, r

def payment():
    session = self.session
    text = self.text.strip().lower()
    phone = self.phone

    # ---------- CONFIRM PAYMENT ----------
    if session.get("state") == "PAYMENT":
    

        if text not in ("yes", "y"):
            self.send("❌ Please complete the payment first and then reply *YES* to confirm.")
            return "", 200

        user_id = session.get("user_id")
        vendor_id = session.get("vendor_id")
        total_amount = session.get("total_price", 0)

        if not user_id or not vendor_id or total_amount <= 0:
            self.send("❌ Payment data missing. Returning to menu.")
            session["state"] = "MENU"
            self.save()
            return "", 200

        with session_scope() as db:
        # 1️⃣ Get user wallet
            wallet = db.query(Wallet).filter_by(user_id=user_id).first()

            user = (
                db.query(User)
                .filter_by(id=user_id)
                .first()
                )

        # 2️⃣ Get vendor
            vendor = (
                db.query(Vendor)
                .filter_by(id=vendor_id, is_verified=True)
                .first()
            )

        if not vendor or not user:
            self.send("❌ Vendor or user not available.")
            session["state"] = "MENU"
            self.save()
            return "", 200

        # 3️⃣ Wallet has enough money → pay vendor directly
        if wallet and wallet.balance >= total_amount:
            try:
                pay_vendor_or_rider(
                    target_type="vendor",
                    target_id=vendor.id,
                    amount=total_amount,
                    narration=f"Food order payment from {user.name} {phone}"
                )

                wallet.debit(db, user.id, total_amount)
                db.commit()

                session["state"] = "MENU"
                self.save()

                self.send(
                    "✅ *Payment Successful!*\n\n"
                    "Vendor has been paid from your wallet.\n\n"
                    + MENU_TEXT
                )
                return "", 200

            except Exception as e:
                db.rollback()
                self.send(f"⚠️ Wallet payment failed: {str(e)}")
                session["state"] = "MENU"
                self.save()
                return "", 200

        # 4️⃣ Wallet insufficient → send vendor Paystack
        self.send(
            "💳 *Wallet balance insufficient*\n\n"
            f"Amount to pay: ₦{total_amount}\n\n"
            f"Please send payment to vendor:\n\n"
            f"🏪 Vendor: {vendor.business_name}\n"
            f"💰 Paystack Account: {vendor.paystack_account}\n\n"
            "After payment, reply *YES* to confirm."
        )
        return "", 200

