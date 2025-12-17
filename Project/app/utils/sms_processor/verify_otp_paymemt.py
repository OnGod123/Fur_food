from functools import wraps
from flask import request, jsonify, render_template, g
from app.extensions import r, session_scope
from app.database.user_models import User
from app.utils.sms_processor.verify_otp import verify_otp_code


def verify_otp_payment(context="payment"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Redis key for OTP verification state
            otp_key = f"otp_verified:{context}:{g.user.id}"

            # 1️⃣ If already verified in Redis → SKIP OTP
            if r.get(otp_key):
                return func(*args, **kwargs)

            # 2️⃣ Work with both JSON API and form submission
            otp = request.form.get("otp") or (request.get_json() or {}).get("otp")

            # 3️⃣ If OTP is not submitted → show OTP form
            if not otp:
                return render_template(
                    "otp_input.html",
                    context=context,
                    phone=g.user.phone,
                    action_url=request.path
                )

            # 4️⃣ Fetch user and validate (SQLAlchemy session)
            with session_scope() as session:
                user = session.get(User, g.user.id)

                if not user or not user.phone:
                    return jsonify({"error": "Phone number not registered"}), 404

                if not verify_otp_code(user.phone, otp, context=context):
                    return jsonify({"error": "Invalid or expired OTP"}), 400

            # 5️⃣ Mark as verified in Redis (persistent across workers)
            r.setex(otp_key, 300, "true")  # 5 minutes

            # 6️⃣ Call the actual handler
            return func(*args, **kwargs)

        return wrapper
    return decorator

