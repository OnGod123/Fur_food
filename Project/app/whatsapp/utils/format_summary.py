def format_summary(session_data):
    lines = ["🧾 Order Summary\n"]

    
    lines.append("Items:")
    for item in session_data.get("items", []):
        subtotal = item["qty"] * item["price"]
        lines.append(
            f"• {item['name']} × {item['qty']} — ₦{subtotal:,}"
        )

    
    address = session_data.get("address")
    if address:
        lines.append("\nDelivery Address:")
        lines.append(address)

    
    total = session_data.get("total", 0)
    lines.append(f"\nTotal:\n₦{total:,}")

    return "\n".join(lines)

