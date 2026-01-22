from flask import Blueprint, request, jsonify
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import r, session_scope
from app.Database.RiderAndStrawler import RiderAndStrawler
from app.Database.user_models import User
from app.utils.jwt_tokens.generate_jwt import generate_rider_jwt
from app.utils.emails.send_email import send_welcome_email
from app.utils.bank.verify_bank_account import resolve_bank_account

sign_up_riderbp = Blueprint("Blueprint_rider_bp", __name__, url_prefix="/rider")

def create_paystack_customer(rider):
    payload = {
        "email": rider.user.email,
        "first_name": rider.account_name.split()[0],
        "last_name": rider.account_name.split()[-1],
        "phone": rider.phone
    }

    res = requests.post(
        "https://api.paystack.co/customer",
        json=payload,
        headers={
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
    )

    data = res.json()

    if data["status"]:
        rider.paystack_customer_code = data["data"]["customer_code"]


def normalize(name: str) -> str:
    return name.lower().strip()

def names_match(bank_name, first, middle, last) -> bool:
    bank_parts = normalize(bank_name).split()
    input_parts = [
        normalize(first),
        normalize(last)
    ]
    if middle:
        input_parts.append(normalize(middle))

    matches = sum(1 for p in input_parts if p in bank_parts)
    return matches >= 2   # require at least 2 matches

@sign_up_riderbp.route("/signup", methods=["GET"])
def rider_show_login_page() -> str:
    return render_template("login.html")

@sign_up_riderbp.route("/signin", methods=["POST"])
def rider_login():
    data = request.get_json() or {}

    email    = data.get("email", "").lower().strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    with session_scope() as session:
        user = session.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({
                "error": "No account found with this email",
                "action": "signup",
                "signup_url": "https://yourapp.com/signup"   # ← or /auth/signup
            }), 404

        if not user.check_password(password):
            return jsonify({"error": "Invalid credentials"}), 401

        rider = session.query(RiderAndStrawler).filter_by(user_id=user.id).first()
        if not rider:
            return jsonify({
                "error": "You are not registered as a rider yet",
                "action": "rider_signup",
                "rider_signup_url": "/rider/signup",   # or full URL
                "message": "Please complete rider onboarding first"
            }), 403

        
        if rider.password_hash and not check_password_hash(rider.password_hash, password):
            return jsonify({"error": "Invalid rider credentials"}), 401

        # ── Successful login ───────────────────────────────────────
        rider.status = "active"
        rider.is_available = True
        rider.last_update = datetime.utcnow()

        # Optional: update phone if sent
        phone = data.get("phone", "").strip()
        if phone and phone != rider.phone:
            rider.phone = phone

        session.commit()

        r.set(f"rider:{user.email}:id", rider.id)

        rider_jwt = generate_rider_jwt(
            user_id=user.id,
            rider_id=rider.id,
            username=user.username or email.split("@")[0]
        )

        return jsonify({
            "message": "Rider login successful",
            "rider_jwt": rider_jwt,
            "redirect_url": "/rider/delivery"
        }), 200

@sign_up_riderbp.route("signup", methods=["POST"])
def rider_signup():
    data = request.get_json() or {}

    email = data.get("email", "").lower().strip()
    username = data.get("username", "").strip()
    password = data.get("password")

    bank_code = data.get("bank_code")
    account_number = data.get("account_number")

    first_name = data.get("first_name", "").strip()
    middle_name = data.get("middle_name", "").strip()
    last_name = data.get("last_name", "").strip()
    phone = data.get("phone", "").strip()

    if not all([email, username, password, bank_code, account_number, first_name, last_name, phone]):
        return jsonify({"error": "Missing required fields"}), 400

    # 🔐 Verify bank account
    bank_data = resolve_bank_account(account_number, bank_code)
    if not bank_data:
        return jsonify({"error": "Bank verification failed"}), 400

    if not names_match(
        bank_data["account_name"],
        first_name,
        middle_name,
        last_name
    ):
        return jsonify({
            "error": "Name mismatch with bank account",
            "bank_name": bank_data["account_name"]
        }), 400

    with session_scope() as session:
        user = session.query(User).filter_by(email=email, username=username).first()
        if not user:
            return jsonify({"error": "Invalid login credentials"}), 401

        rider = session.query(RiderAndStrawler).filter_by(user_id=user.id).first()
        if rider:
            return jsonify({"error": "User has been regoistered has rider login"}), 403

        # Password handling
        rider = RiderAndStrawler(
                user_id=user.id,
                nin=nin,
                phone=phone,
                address=data.get("address", ""),               # add if you collect it
                identification_number=nin,                     # or separate field
                status="active",
                is_available=True,
                is_verified=True,
                bank_code=bank_code,
                account_number=account_number,
                account_name=bank_data["account_name"],
                bank_name=bank_data.get("bank_name", "Verified Bank"),
                last_update=datetime.utcnow()
            )
        rider.set_password(password)   # if you want separate rider password
        session.add(rider)
        session.flush()
        session.commit()
        r.set(f"rider:{user.email}:id", rider.id)
        rider_jwt = generate_rider_jwt(
            user_id=user.id,
            rider_id=rider.id,
            username=user.username
        )
    create_paystack_customer(rider)
    create_dedicated_account(rider)
    send_welcome_email(user.email, user.username)

    return jsonify({
        "message": "Rider verified and login successful",
        "redirect_url": "/rider/delivery",
        "rider_jwt": rider_jwt
    }), 200

