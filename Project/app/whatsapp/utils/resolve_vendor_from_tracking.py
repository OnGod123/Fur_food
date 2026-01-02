from app.Database.order_single import OrderSingle
from app.Database.order_multiple import OrderMultiple
from app.Database.vendors_model import Vendor
from app.extensions import session_scope


def resolve_vendor_from_tracking(tracking_id: str) -> dict:
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
            "business_name": vendor.business_name
        }

