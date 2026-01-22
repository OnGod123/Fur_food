from flask import Blueprint, request, current_app, abort, g
import requests
from flask import Blueprint, request, jsonify, current_app
from app.utils.bank.verify_bank_account import resolve_bank_account
from sqlalchemy.orm import sessionmaker
from app.extensions import SessionLocal
from app.utils.bank.assign_bank import create_dedicated_account
from app.utils.bank.assign_bank import create_paystack_customer_code

admin_bp = Blueprint("admin_bp", __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = getattr(g, 'user', None)
        if not user or not getattr(user, 'is_admin', False):
            abort(403)
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/admin/create_paystack_account', methods=['POST'])
@admin_required
def create_admin_paystack():
    admin_entity = g.user
    result = create_dedicated_account(admin_entity)
    return {"status": "success", "account": result}

@admin_bp.route('/admin/delete_user/<phone>', methods=['POST'])
@admin_required
def delete_user(phone):
    # Assuming Redis for user data
    user_key = f"user:{phone}"
    redis.delete(user_key)
    return {"status": "deleted"}

@admin_bp.route("/signup", methods=["POST"])
def admin_signup():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    bank_code = data.get("bank_code", "")
    account_number = data.get("account_number", "")
    
    first_name = data.get("first_name", "").strip()
    middle_name = data.get("middle_name", "").strip()
    last_name = data.get("last_name", "").strip()
    phone = data.get("phone", "").strip()

    if not all([email, username, password, bank_code, account_number, first_name, last_name, phone]):
        return jsonify({"error": "Missing required fields"}), 400

    session = SessionLocal()
    try:
        admin_count = session.query(Admin).count()
        if admin_count >= 3:
            return jsonify({"error": "Maximum number of admins reached"}), 403

        if session.query(Admin).filter((Admin.email==email)|(Admin.username==username)).first():
            return jsonify({"error": "Admin with this username or email exists"}), 409

        # Verify bank account
        bank_data = resolve_bank_account(account_number, bank_code)
        if not bank_data:
            return jsonify({"error": "Bank verification failed"}), 400
        
        def normalize(name: str) -> str:
            return name.lower().strip()
        def names_match(bank_name, first, middle, last) -> bool:
            bank_parts = normalize(bank_name).split()
            input_parts = [normalize(first), normalize(last)]
            if middle:
                input_parts.append(normalize(middle))
            matches = sum(1 for p in input_parts if p in bank_parts)
            return matches >= 2

        if not names_match(bank_data["account_name"], first_name, middle_name, last_name):
            return jsonify({
                "error": "Name mismatch with bank account",
                "bank_name": bank_data["account_name"]
            }), 400

        admin = Admin(
            username=username,
            email=email,
            bank_code=bank_code,
            account_number=account_number,
            account_name=bank_data["account_name"]
        )
        admin.set_password(password)
        session.add(admin)
        session.flush()  

        admin_data = type("AdminData", (), {})()
        admin_data.user = type("User", (), {})()
        admin_data.user.email = email
        admin_data.account_name = bank_data["account_name"]
        admin_data.phone = phone
        create_paystack_customer(admin_data)
        # persist customer code in admin
        admin.paystack_customer_code = getattr(admin_data, "paystack_customer_code", None)
        # create dedicated account
        if admin.paystack_customer_code:
            paystack_acc = create_dedicated_account(admin)
            admin.paystack_virtual_account = paystack_acc.get("account_number")
        
        session.commit()
        save_account_number_to_env(admin.paystack_virtual_account, key="ADMIN_ACCOUNT_NUMBER", env_path=".env")
        return jsonify({"message": "Admin account created successfully."}), 201
    finally:
        session.close()

