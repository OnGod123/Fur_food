import jwt
import hashlib
from datetime import datetime, timedelta
from flask  import current_app

def generate_vendor_jwt(vendor_id: int, business_name: str, vendor_password: str):
    """
    vendor_password is hashed before adding into payload.
    """
    hash_pass = hashlib.sha256(vendor_password.encode()).hexdigest()

    payload = {
        "vendor_id": vendor_id,
        "business_name": business_name,
        "signature": hash_pass,     
        "exp": datetime.utcnow() + timedelta(days=7)
    }

    token = jwt.encode(payload, current_app.config["secret_key"].upper, algorithm="HS256")
    return token



def decode_vendor_jwt(vendor_token: str):
    try:
        payload = jwt.decode(vendor_token, current_app.config['secret_key'].upper, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise PermissionError("Vendor token expired")
    except jwt.InvalidTokenError:
        raise PermissionError("Invalid vendor token")
