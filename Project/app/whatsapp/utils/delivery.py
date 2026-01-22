from app.Database.delivery import Delivery


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




def redirect_to_delivery(delivery_id):
    """
    Returns the delivery bargain/location URL
    """
    return url_for(
        "delivery_bp.manage_delivery_location",
        delivery_id=delivery_id,
        _external=True
    )


