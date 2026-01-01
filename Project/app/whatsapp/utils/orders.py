from app.Database.order import OrderSingle

def build_order(
    session,
    *,
    user_id,
    vendor_id,
    items,
    address,
):
    total = sum(item["price"] * item["qty"] for item in items)

    order = OrderSingle(
        user_id=user_id,
        vendor_id=vendor_id,
        item_data=items,
        total=total,
        product_name=", ".join(i["name"] for i in items),
        recipient_address=address,
    )

    session.add(order)
    session.flush()   

    return order

