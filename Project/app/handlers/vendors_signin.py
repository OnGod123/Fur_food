from flask import Blueprint, request, jsonify, g
from datetime import datetime
from app.extensions import r, session_scope
from app.Database.vendors_model import Vendor
from app.utils.jwt_tokens.vendor_token import generate_vendor_jwt
from app.utils.jwt_tokens.verify_user import verify_jwt_token

bp_vendor_register = Blueprint("Blueprint_vendor_bp", __name__, url_prefix="/vendor")

def create_paystack_customer_for_vendor(vendor):
    payload = {
        "email": vendor.business_email,
        "first_name": vendor.business_name.split()[0],
        "last_name": vendor.business_name.split()[-1],
        "phone": vendor.business_phone
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

    if not data.get("status"):
        raise Exception(data.get("message", "Paystack error"))

    vendor.paystack_customer_code = data["data"]["customer_code"]


@verify_jwt_token
@bp_vendor_register.route("/signup", methods=["POST"])
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

    
    if not all([business_name, business_address, vendor_password,
                bussiness_account, bank_code, account_number]):
        return jsonify({
            "error": "All fields are required: business_name, business_address, "
                     "vendor_password, Bussiness_account, bank_code, account_number"
        }), 400

    with session_scope() as session:
        existing_vendor = session.query(Vendor).filter_by(user_id=user.id).first()
        if existing_vendor:
            return jsonify({"error": "User already registered as vendor"}), 400

        
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


        create_paystack_customer_for_vendor(vendor)
        session.add(new_vendor)
        session.flush()  


        r.set(f"vendor:{user.email}:id", new_vendor.id)

        
        vendor_jwt = generate_vendor_jwt(
        vendor_id=new_vendor.id,
        business_name=business_name,
        vendor_password=vendor_password
        )


    
    return jsonify({
        "message": "Vendor registration successful",
        "vendor": new_vendor.to_dict(),
        "vendor_jwt": vendor_jwt
    }), 201

