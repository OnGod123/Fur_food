from flask import Flask, jsonify, request, Blueprint
from sqlalchemy.orm import Session
from app.Database.RiderAndStrawler import RiderAndStrawler
from app.Database.vendors_model import Vendor       # ← changed 'vendor' → 'Vendor' (class name convention)
from app.extensions import session_scope as session   # assuming this is your scoped session factory

Dashboard_bp = Blueprint("home_bp", __name__, url_prefix="/database")

@Dashboard_bp.route('/nearby', methods=['GET'])     # ← added Blueprint decorator + fixed route path
def get_nearby():
    phone = request.args.get('phone')
    if not phone:
        return jsonify({"error": "phone is required"}), 400

    home = get_home_location(phone)
    if not home:
        return jsonify({"error": "no home location found"}), 404

    lat, lng = home['lat'], home['lng']

    vendors_nearby = find_nearby_vendors(lat, lng)
    riders_nearby = find_nearby_rider(lat, lng)

    expanded_vendors = []
    with session() as db:                           # ← most common pattern: session()
        vendor_ids = [v["vendor_id"] for v in vendors_nearby]
        vendor_objs = db.query(Vendor).filter(Vendor.id.in_(vendor_ids)).all()
        vendor_dict = {v.id: v for v in vendor_objs}

        for v in vendors_nearby:
            vendor_obj = vendor_dict.get(v["vendor_id"])
            if vendor_obj:
                expanded_vendor = {
                    "vendor_id": v["vendor_id"],
                    "distance_m": v["distance_m"],
                    "lat": v["lat"],
                    "lng": v["lng"],
                    "coordinate": {"lat": v["lat"], "lng": v["lng"]},
                    "business_name": vendor_obj.business_name,
                    "business_address": vendor_obj.business_address,
                    "business_email": vendor_obj.business_email,
                    "business_phone": vendor_obj.business_phone,
                    "is_open": vendor_obj.is_open,
                    "is_verified": vendor_obj.is_verified,
                    "account_name": vendor_obj.account_name,
                    "account_number": vendor_obj.account_number,
                    "bank_code": vendor_obj.bank_code,
                    "bank_name": vendor_obj.bank_name,
                    "paystack_customer_code": vendor_obj.paystack_customer_code,
                    "paystack_virtual_account": vendor_obj.paystack_virtual_account,
                    "created_at": str(vendor_obj.created_at),
                    "updated_at": str(vendor_obj.updated_at),
                }
                expanded_vendors.append(expanded_vendor)

    expanded_riders = []
    with session() as db:
        rider_ids = [r["rider_id"] for r in riders_nearby]
        rider_objs = db.query(RiderAndStrawler).filter(RiderAndStrawler.id.in_(rider_ids)).all()
        rider_dict = {r.id: r for r in rider_objs}

        for r in riders_nearby:
            rider_obj = rider_dict.get(r["rider_id"])
            if rider_obj:
                expanded_rider = {
                    "rider_id": r["rider_id"],
                    "distance_m": r["distance_m"],
                    "lat": r["lat"],
                    "lng": r["lng"],
                    "coordinate": {"lat": r["lat"], "lng": r["lng"]},
                    "phone": rider_obj.phone,
                    "status": rider_obj.status,
                    "is_verified": rider_obj.is_verified,
                    "address": rider_obj.address,
                    "completed_rides": rider_obj.completed_rides,
                    "bank_name": rider_obj.bank_name,
                    "bank_code": rider_obj.bank_code,
                    "account_name": rider_obj.account_name,
                    "account_number": rider_obj.account_number,
                    "paystack_customer_code": rider_obj.paystack_customer_code,
                    "paystack_virtual_account": rider_obj.paystack_virtual_account,
                    "last_update": str(rider_obj.last_update)
                }
                expanded_riders.append(expanded_rider)

    return jsonify({
        "home_location": home,
        "vendors": expanded_vendors,
        "riders": expanded_riders,
    })
