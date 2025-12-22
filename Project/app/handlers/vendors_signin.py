from flask import Blueprint, request, jsonify, g
from datetime import datetime
from app.extensions import r, session_scope
from app.database.vendor_models import Vendor
from app.utils.jwt_tokens.vendor_token import generate_vendor_jwt
from app.utils.jwt_tokens.authentication import token_required

vendor_bp_signin = Blueprint("vendor_bp", __name__)


@verify_jwt_token
@vendor_bp_signin.route("/vendor/signup", methods=["POST"] url_prefix="/vendor/signin")
def signup_vendor():
    """
    Signup a new vendor.
    Requires a valid user JWT.
    Returns vendor JWT after creation.
    """
    user = g.user
    data = request.get_json() or {}

    business_name = data.get("business_name")
    business_address = data.get("business_address")
    vendor_password = data.get("vendor_password")  
    bussiness_account = data.get("Bussiness_account")
    bank_code = data.get("bank_code")
    account_number = data.get("account_number")

    # Validate required fields
    if not all([business_name, business_address, vendor_password,
                bussiness_account, bank_code, account_number]):
        return jsonify({
            "error": "All fields are required: business_name, business_address, "
                     "vendor_password, Bussiness_account, bank_code, account_number"
        }), 400

    with session_scope() as session:
        # Check if user is already a vendor
        existing_vendor = session.query(Vendor).filter_by(user_id=user.id).first()
        if existing_vendor:
            return jsonify({"error": "User already registered as vendor"}), 400

        # Create vendor record
        new_vendor = Vendor(
            Business_name=business_name,
            Business_address=business_address,
            Bussiness_account=bussiness_account,
            bank_code=bank_code,
            account_number=account_number,
            created_at=datetime.utcnow(),
            is_open=True,
            user_id=user.id
        )

        session.add(new_vendor)
        session.flush()  # flush to get new_vendor.id before commit

        # Cache vendor ID in Redis
        r.set(f"vendor:{user.email}:id", new_vendor.id)

        # Generate vendor JWT
        vendor_jwt = generate_vendor_jwt(
        vendor_id=new_vendor.id,
        business_name=business_name,
        vendor_password=vendor_password
        )


    # Commit happens automatically at the end of session_scope() block
    return jsonify({
        "message": "Vendor registration successful",
        "vendor": new_vendor.to_dict(),
        "vendor_jwt": vendor_jwt
    }), 201

