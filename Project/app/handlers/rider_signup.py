from flask import Blueprint, request, jsonify
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import r, session_scope
from app.Database.RiderAndStrawler import RiderAndStrawler
from app.Database.user_models import User
from app.utils.jwt_tokens.generate_jwt import generate_rider_jwt
from app.utils.emails.send_email import send_welcome_email
from app.utils.bank.verify_bank_account import resolve_bank_account

bp_rider_login = Blueprint("Blueprint_rider_bp", __name__, url_prefix="/rider")

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


@bp_rider_login.route("/login", methods=["POST"])
def login_rider():
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
        # Authenticate user
        user = session.query(User).filter_by(email=email, username=username).first()
        if not user:
            return jsonify({"error": "Invalid login credentials"}), 401

        rider = session.query(RiderAndStrawler).filter_by(user_id=user.id).first()
        if not rider:
            return jsonify({"error": "User is not registered as a rider"}), 403

        # Password handling
        if not rider.password_hash:
            rider.password_hash = generate_password_hash(password)
        elif not check_password_hash(rider.password_hash, password):
            return jsonify({"error": "Invalid rider credentials"}), 401

        # ✅ Verified & activated
        rider.status = "active"
        rider.is_available = True
        rider.is_verified = True
        rider.phone = phone
        rider.bank_code = bank_code
        rider.account_number = account_number
        rider.account_name = bank_data["account_name"]
        rider.last_update = datetime.utcnow()
        create_paystack_customer(rider)

        session.flush()

        r.set(f"rider:{user.email}:id", rider.id)

        rider_jwt = generate_rider_jwt(
            user_id=user.id,
            rider_id=rider.id,
            username=user.username
        )

    send_welcome_email(user.email, user.username)

    return jsonify({
        "message": "Rider verified and login successful",
        "redirect_url": "/rider/delivery",
        "rider_jwt": rider_jwt
    }), 200

