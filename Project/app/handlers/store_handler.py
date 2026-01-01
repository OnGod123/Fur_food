from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import or_
from app.Database.food_item import FoodItem
from app.Database.vendors_model import Vendor
from app.utils.minio.minio_utils import get_minio_file_url
from app.extensions import session_scope, r

store_bp = Blueprint("store_bp", __name__, url_prefix="/items")
PAGE_SIZE = 10

# ------------------- Store listing -------------------
@store_bp.route("/store", methods=["GET"])
def stream_store_items():
    global r
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    cache_key = f"store:page:{page}"
    if r:
        cached = r.get(cache_key)
        if cached:
            return jsonify(json.loads(cached)), 200

    with session_scope() as session:
        offset = (page - 1) * PAGE_SIZE

        items = (
            session.query(FoodItem)
            .join(Vendor, Vendor.id == FoodItem.vendor_id)
            .filter(FoodItem.is_available.is_(True), Vendor.is_open.is_(True))
            .order_by(FoodItem.created_at.desc())
            .limit(PAGE_SIZE)
            .offset(offset)
            .all()
        )

        result = []
        for item in items:
            item_dict = item.to_dict()
            if item.image_url:
                try:
                    item_dict["image_url"] = get_minio_file_url(item.vendor_name, item.image_url)
                except Exception:
                    item_dict["image_url"] = None
            result.append(item_dict)

        response_dict = {
            "page": page,
            "page_size": PAGE_SIZE,
            "count": len(result),
            "items": result
        }

        if r:
            try:
                r.set(cache_key, json.dumps(response_dict), ex=300)
            except Exception as e:
                current_app.logger.error(f"Redis caching failed: {str(e)}")

        return jsonify(response_dict), 200

# ------------------- Search -------------------
@store_bp.route("/store/searchfood", methods=["GET"])
def search_store_items():
    global r
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    cache_key = f"store:search:{q}:page:{page}"
    if r:
        cached = r.get(cache_key)
        if cached:
            return jsonify(json.loads(cached)), 200

    with session_scope() as session:
        offset = (page - 1) * PAGE_SIZE
        query = session.query(FoodItem).join(Vendor, Vendor.id == FoodItem.vendor_id).filter(
            FoodItem.is_available.is_(True),
            Vendor.is_open.is_(True)
        )

        if q:
            query = query.filter(
                or_(
                    FoodItem.item_name.ilike(f"%{q}%"),
                    FoodItem.product_name.ilike(f"%{q}%"),
                    FoodItem.vendor_name.ilike(f"%{q}%"),
                    FoodItem.description.ilike(f"%{q}%"),
                    FoodItem.item_description.ilike(f"%{q}%")
                )
            )

        items = query.order_by(FoodItem.created_at.desc()).limit(PAGE_SIZE).offset(offset).all()

        result = []
        for item in items:
            item_dict = item.to_dict()
            if item.image_url:
                try:
                    item_dict["image_url"] = get_minio_file_url(item.vendor_name, item.image_url)
                except Exception:
                    item_dict["image_url"] = None
            result.append(item_dict)

        response_dict = {
            "page": page,
            "page_size": PAGE_SIZE,
            "count": len(result),
            "items": result
        }

        if r:
            try:
                r.set(cache_key, json.dumps(response_dict), ex=300)
            except Exception as e:
                current_app.logger.error(f"Redis caching failed: {str(e)}")

        return jsonify(response_dict), 200

# ------------------- Vendor open/close shop -------------------
@store_bp.route("/vendor/toggle_shop", methods=["POST"])
def toggle_vendor_shop():
    data = request.get_json() or {}
    vendor_id = data.get("vendor_id")
    open_state = data.get("is_open")

    if vendor_id is None or open_state is None:
        return jsonify({"error": "vendor_id and is_open required"}), 400

    with session_scope() as session:
        vendor = session.query(Vendor).filter_by(id=vendor_id).first()
        if not vendor:
            return jsonify({"error": "Vendor not found"}), 404

        vendor.is_open = bool(open_state)
        return jsonify({"message": f"Vendor shop {'opened' if vendor.is_open else 'closed'} successfully"}), 200

