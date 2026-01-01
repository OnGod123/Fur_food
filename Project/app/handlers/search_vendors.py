from flask import Blueprint
from flask import jsonify, request, current_app
from app.Database.food_item import FoodItem
from app.Database.vendors_model import Vendor
from app.extensions import session_scope, r
from app.utils.minio.minio_utils import get_minio_file_url

PAGE_SIZE = 10  # example

search_for_vendor_bp = Blueprint("search_for_vendor", __name__, url_prefix="/api/vendors")

# Register route
@search_for_vendor_bp.route("/search", methods=["GET"])
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

    offset = (page - 1) * PAGE_SIZE

    with session_scope() as session:
        # Only filter vendors by name
        vendors_query = session.query(Vendor).filter(
            Vendor.is_open.is_(True)
        )
        if q:
            vendors_query = vendors_query.filter(
                Vendor.Business_name.ilike(f"%{q}%")
            )

        vendors = vendors_query.order_by(Vendor.created_at.desc()).offset(offset).limit(PAGE_SIZE).all()

        result = []

        for vendor in vendors:
            # Get all available food items for this vendor
            food_items = session.query(FoodItem).filter(
                FoodItem.vendor_id == vendor.id,
                FoodItem.is_available.is_(True)
            ).order_by(FoodItem.created_at.desc()).all()

            items_list = []
            for item in food_items:
                item_dict = item.to_dict()
                if item.image_url:
                    try:
                        item_dict["image_url"] = get_minio_file_url(item.vendor_name, item.image_url)
                    except Exception:
                        item_dict["image_url"] = None
                items_list.append(item_dict)

            # Append vendor profile + all food items
            result.append({
                "profile": {
                    "name": vendor.Business_name,
                    "is_open": vendor.is_open,
                    "opening_time": vendor.opening_time.strftime("%H:%M") if vendor.opening_time else None,
                    "closing_time": vendor.closing_time.strftime("%H:%M") if vendor.closing_time else None,
                    "business_address": vendor.Business_address
                },
                "items": items_list
            })

        response_dict = {
            "page": page,
            "page_size": PAGE_SIZE,
            "count": len(result),
            "vendors": result
        }

        if r:
            try:
                r.set(cache_key, json.dumps(response_dict), ex=300)  # cache for 5 minutes
            except Exception as e:
                current_app.logger.error(f"Redis caching failed: {str(e)}")

        return jsonify(response_dict), 200

