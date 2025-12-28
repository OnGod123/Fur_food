from functools import wraps
from flask import jsonify, request
from app.extensions import r, SessionLocal  # SessionLocal is your SQLAlchemy session factory
from app.Database.vendors_model import Vendor
import json

VENDOR_STATUS_TTL = 300  # seconds

def get_cached_vendor_status(vendor_id):
    key = f"vendor_status:{vendor_id}"
    val = r.get(key)
    if val is None:
        return None
    # stored as "open" or "closed"
    return val.decode("utf-8")

def cache_vendor_status(vendor_id, status):
    key = f"vendor_status:{vendor_id}"
    r.setex(key, VENDOR_STATUS_TTL, status)
    # publish change for other processes
    r.publish("vendor_status_changes", json.dumps({"vendor_id": vendor_id, "status": status}))

def get_session():
    """Return a SQLAlchemy session."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db(app) first.")
    return SessionLocal()

def vendor_must_be_open(fn):
    """
    Decorator to ensure target vendor is open.
    Expects `vendor_id` in URL params, JSON body, or query string.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        vendor_id = None

        # Check URL parameters first
        if request.view_args:
            vendor_id = request.view_args.get("vendor_id")

        # Check JSON body or query string if not found
        if not vendor_id:
            data = request.get_json(silent=True) or {}
            vendor_id = data.get("vendor_id") or request.args.get("vendor_id")

        if not vendor_id:
            return jsonify({"error": "vendor_id is required"}), 400

        # Check cache
        status = get_cached_vendor_status(vendor_id)

        if status is None:
            # Fallback to DB
            session = get_session()
            vendor = session.query(Vendor).get(vendor_id)
            if not vendor:
                return jsonify({"error": "Vendor not found"}), 404

            # Determine status: you can adapt the field name
            status = "open" if getattr(vendor, "is_open", getattr(vendor, "is_active", True)) else "closed"

            # Cache the result
            cache_vendor_status(vendor_id, status)

        if status != "open":
            return jsonify({"error": "Vendor currently closed"}), 403

        return fn(*args, **kwargs)

    return wrapper

