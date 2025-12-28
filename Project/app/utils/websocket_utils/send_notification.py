from app.utils.websocket_utils.websocket_redis import search_chat_room
from app.extensions import emit_to_room
from app.Database.notifications import Notification
from app.Database.vendors_model import Vendor

def send_notification_async(self, vendor_business_name, username, notif_dict):
    room_id = search_chat_room(username, vendor_business_name)
    if not room_id:
        room_id = generate_shared_room(username, vendor_business_name)

    emit_to_room(room_id, "new_notification", notif_dict)

