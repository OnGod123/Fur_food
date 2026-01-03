from app.Database.order_single import OrderSingle
from app.Database.order_multiple import OrderMultiple
from app.Database.vendors_model import Vendor
from app.extensions import session_scope
from flask import url_for


def resolve_vendor(tracking_id: str) -> dict:
    """
    Resolve vendor identity using tracking_id or order reference.
    """

    with session_scope() as session:

        # Try single order first
        order = (
            session.query(OrderSingle)
            .filter_by(reference=tracking_id)
            .first()
        )

        # If not found, try multiple order
        if not order:
            order = (
                session.query(OrderMultiple)
                .filter_by(reference=tracking_id)
                .first()
            )

        if not order:
            raise ValueError("Order not found for tracking ID")

        vendor = session.query(Vendor).get(order.vendor_id)
        if not vendor:
            raise ValueError("Vendor not found")

        return {
            "vendor_id": vendor.id,
            "vendor_username": vendor.username,
            "business_name": vendor.business_name
        }

def resolve_buyer(phone: str) -> dict:
    """
    Resolve buyer identity using WhatsApp (KAT) phone number.
    Source of truth: Redis session.
    """

    session_data = load_session(phone)

    username = session_data.get("username")
    user_id = session_data.get("user_id")

    if not username or not user_id:
        raise ValueError("Buyer not authenticated or session expired")

    return {
        "user_id": int(user_id),
        "username": username
    }





def redirect_to_bargain(buyer_username: str, vendor_username: str) -> str:
    """
    Build a private chat URL between buyer and vendor.
    Returns a URL string.
    """
    return url_for(
        "private_chat.private",
        user=buyer_username,
        peer=vendor_username,
        _external=True
    )

