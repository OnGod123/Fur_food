from app.merchants.Database.delivery import Delivery
from app.riders.services import auto_assign_rider

def create_delivery(
    session,
    *,
    user_id,
    order_id,
    address,
):
    delivery = Delivery(
        user_id=user_id,
        order_id=order_id,
        address=address,
        status="pending",
    )

    session.add(delivery)
    session.flush()   

    return delivery




