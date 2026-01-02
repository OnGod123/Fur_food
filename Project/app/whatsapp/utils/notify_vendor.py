from contextlib import contextmanager
from app.Database.notification import Notification
from app.extensions import Base, session_scope


def notify_vendor_new_order(order):
    """
    Create a vendor notification for a new order.
    Stores only the reference to the order (order.id),
    without returning anything.
    """

    notification = Notification(
        user_id=order.vendor.user_id,  
        vendor_id=order.vendor_id,
        order_id=str(order.id),
        type="new_single_order",       
        payload=None                   
    )

    # Insert into DB using session_scope
    with session_scope() as session:
        session.add(notification)
        # commit happens automatically when context exits

