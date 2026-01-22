
from app.whatsapp.utils.ai.ai_step_guard.py import ai_guard_step

def ask_item(self):
    session = self.session
    text = self.text
    state = session.get("state")

    # ---------- ASK ITEMS ----------
    if state == "ASK_ITEMS":
        result = ai_guard_step(
            step="ASK_ITEMS",
            user_input=text,
            expected="Send the item number from the menu",
            examples=["1", "2", "3"],
        )

        items_menu = session.get("items_menu", {})

        if not result["ok"] or result["value"] not in items_menu:
            self.send("❌ Invalid item selection. Please reply with a valid item number.")
            return "", 200

        selected_item = items_menu[result["value"]]

        session["selected_item"] = selected_item
        session["state"] = "ASK_QUANTITY"
        self.save()

        self.send(
            f"🧮 How many *{selected_item['name']}* do you want?\n"
            "Reply with a number (default is 1)."
        )
        return "", 200

    # ---------- ASK QUANTITY ----------
    if state == "ASK_QUANTITY":
        quantity = 1

        if text.strip().isdigit():
            quantity = int(text.strip())
            if quantity < 1:
                quantity = 1

        item = session.get("selected_item")

        if not item:
            session["state"] = "MENU"
            self.save()
            self.send("❌ No item selected.")
            return "", 200

        total_price = item["price"] * quantity

        session["quantity"] = quantity
        session["total_price"] = total_price
        session["state"] = "PAYMENT"
        self.save()

        self.send(
            "🧾 *Order Summary*\n\n"
            f"Item: {item['name']}\n"
            f"Quantity: {quantity}\n"
            f"Unit Price: ₦{item['price']}\n"
            f"Total: ₦{total_price}\n\n"
            "💳 Proceeding to payment..."
        )
        return "", 200

    return "", 200

