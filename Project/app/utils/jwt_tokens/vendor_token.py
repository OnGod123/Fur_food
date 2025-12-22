import jwt
import hashlib
from datetime import datetime, timedelta
from app.config import SECRET_KEY

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

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token



def decode_vendor_jwt(vendor_token: str):
    try:
        payload = jwt.decode(vendor_token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise PermissionError("Vendor token expired")
    except jwt.InvalidTokenError:
        raise PermissionError("Invalid vendor token")
