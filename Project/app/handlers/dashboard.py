from flask import Blueprint, jsonify, request
from app.extensions import Base, r
from app.Database.vendors_model import Vendor 
from app.database.fooditem import FoodItem
from app.utils.minio_utils import get_minio_file_url
import json
from datetime import timedelta

@dashboard = Blueprint("vendor_bp", __name__, url_prefix="/dashboard")


@dashboard.route("/vendors/dashboard", methods=["GET"])
def vendor_dashboard():
    """
    Vendor dashboard endpoint with Redis caching.

    Displays all open vendors along with their available food items.
    Supports optional search and pagination. Food items include
    MinIO image URLs if available. Cached in Redis for 5 minutes.

    Query Parameters
    ----------------
    search : str, optional
        Search string to filter vendors by name (default: "").
    page : int, optional
        Page number for pagination (default: 1).
    limit : int, optional
        Number of vendors per page (default: 10).

    Returns
    -------
    Response
        JSON response with:
        - page: Current page
        - limit: Number of vendors per page
        - total_vendors: Total vendors matching query
        - total_pages: Total number of pages
        - vendors: List of vendor dictionaries including food items
    """
    search = request.args.get("search", "").strip().lower()
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    offset = (page - 1) * limit

    cache_key = f"vendors_dashboard:{search or 'all'}:page:{page}:limit:{limit}"

    cached_data = r.get(cache_key)
    if cached_data:
        print("[CACHE HIT] Returning paginated vendors from Redis cache.")
        return jsonify(json.loads(cached_data)), 200

    print("[CACHE MISS] Fetching vendors from DB...")
    query = Vendor.query.filter_by(is_open=True)
    if search:
        query = query.filter(Vendor.name.ilike(f"%{search}%"))

    total_vendors = query.count()
    vendors = query.offset(offset).limit(limit).all()

    result = {
        "page": page,
        "limit": limit,
        "total_vendors": total_vendors,
        "total_pages": (total_vendors + limit - 1) // limit,
        "vendors": []
    }

    for v in vendors:
        food_items = FoodItem.query.filter_by(
            vendor_id=v.id,
            is_available=True
        ).all()

        items_list = []
        for item in food_items:
            item_dict = {
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "description": getattr(item, "description", None),
                "picture_filename": getattr(item, "picture_filename", None),
                "picture_type": getattr(item, "picture_type", None),
                "vendor_name": getattr(item, "vendor_name", v.name),
                "is_available": item.is_available,
            }

            if getattr(item, "available_from", None):
                item_dict["available_from"] = item.available_from.strftime("%H:%M")
            else:
                item_dict["available_from"] = None

            if getattr(item, "available_to", None):
                item_dict["available_to"] = item.available_to.strftime("%H:%M")
            else:
                item_dict["available_to"] = None

            try:
                if item_dict["vendor_name"] and item_dict["picture_filename"]:
                    image_url = get_minio_file_url(item_dict["vendor_name"], item_dict["picture_filename"])
                else:
                    image_url = None
            except Exception as e:
                print(f"[MINIO ERROR] vendor={v.id} item={item.id} error={e}")
                image_url = None

            item_dict["image_url"] = image_url
            items_list.append(item_dict)

        result["vendors"].append({
            "vendor_id": v.id,
            "vendor_name": v.name,
            "status": "open" if v.is_open else "closed",
            "location": v.location,
            "category": v.category,
            "average_rating": v.average_rating,
            "banner_image": v.banner_image,
            "food_items": items_list
        })

    r.setex(cache_key, timedelta(minutes=5), json.dumps(result))
    return jsonify(result), 200
