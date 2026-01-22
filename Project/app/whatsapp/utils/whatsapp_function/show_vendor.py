from app.Database.food_item import FoodItem 
from app.whatsapp.utils.ai.ai_step_guard import ai_guard_step
from app.Database.user_models import User
from app.Database.vendors_model import Vendor
from app.extensions import session_scope, r

def show_vendor_menu(self):
    """
    Sends the vendor's menu to the user.
    Precondition: session['state'] must be 'SHOW_VENDOR_MENU'.
    Only changes state if moving to the next step.
    """

    session = self.session
    state = session.get("state")
    vendor_id = session.get("vendor_id")

    # Only proceed if state is SHOW_VENDOR_MENU
    if state == "SHOW_VENDOR_MENU":
 
        if not vendor_id:
            session["state"] = "MENU"
            self.save()
            self.send("❌ Vendor not selected. Returning to main menu.")
            return "", 200

    # Fetch up to 10 food items for this vendor
        with session_scope() as db:
            items = db.query(FoodItem).filter(FoodItem.vendor_id == vendor_id).limit(10).all()

    # If no items, fallback to custom order
        if not items:
            session["state"] = "CUSTOM_ITEM"
            self.save()
            self.send(
                "ℹ️ This vendor has no listed menu yet.\n"
                "Please describe what you want to order (custom item)."
            )
            return "", 200

    # Build menu map and message
        menu_map = {}
        menu_lines = []

        for idx, item in enumerate(items, start=1):
            menu_map[str(idx)] = {
                "id": item.id,
                "name": item.name,
                "price": item.price,
            }
            menu_lines.append(f"{idx}) {item.name} — ₦{item.price}")

    # Save menu map in session and move to item selection
        session["items_menu"] = menu_map
        session["state"] = "ASK_ITEMS"  # Only state change
        self.save()

    # Send formatted menu to user
        self.send(
        "🍴 *Vendor Menu*\n\n"
        + "\n".join(menu_lines)
        + "\n\nReply with the item number or describe a custom order."
        )

    return "", 200

