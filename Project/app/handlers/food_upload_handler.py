import base64
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g
from app.extensions import session_scope as session
from app.Database.food_item import FoodItem
from app.Database.vendors_model import Vendor
from app.Database.user_models import User
from app.utils.jwt_tokens.generate_jwt import decode_jwt_token  # your JWT decoder
from app.utils.minio.minio_utils import upload_to_minio, get_minio_file_url
from app.utils.file_utils import validate_image_bytes
from app.utils.jwt_tokens.authentication import vendor_required

food_bp = Blueprint("food", __name__, url_prefix="/api/food")
@vendor_required
@food_bp.route("/items", methods=["POST"])
@vendor_required
def add_food_item():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "Missing JSON data"}), 400

    try:
        vendor_id = g.vendor.id
        vendor_name = g.vendor.Business_name

        # Required fields
        required_fields = ["product_name", "item_name", "item_description", "price"]
        missing = [f for f in required_fields if f not in payload]
        if missing:
            return jsonify({"error": f"Missing required fields: {missing}"}), 400

        product_name = payload["product_name"]
        item_name = payload["item_name"]
        item_description = payload["item_description"]
        price = float(payload["price"])
        picture_filename = payload.get("picture_filename")
        picture_type = payload.get("picture_type")
        picture_data = payload.get("picture_data")
        available_from = payload.get("available_from")
        available_to = payload.get("available_to")

        image_url = None
        if picture_filename and picture_type and picture_data:
            file_bytes = base64.b64decode(picture_data)
            validate_image_bytes(file_bytes, picture_filename)
            upload_to_minio(vendor_name, file_bytes, picture_filename, picture_type)
            image_url = get_minio_file_url(vendor_name, picture_filename)

        new_item = FoodItem(
            vendor_id=vendor_id,
            merchant_id=g.user.id,
            product_name=product_name,
            vendor_name=vendor_name,
            item_name=item_name,
            item_description=item_description,
            price=price,
            image_url=image_url,
            is_available=True,
            available_from=datetime.strptime(available_from, "%H:%M").time() if available_from else None,
            available_to=datetime.strptime(available_to, "%H:%M").time() if available_to else None
        )

        with session_scope() as db_session:
            db_session.add(new_item)

        return jsonify({
            "message": "Food item added successfully",
            "food_item": new_item.to_dict()
        }), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to add food item", "details": str(e)}), 500

