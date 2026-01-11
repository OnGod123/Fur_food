from flask import Blueprint, render_template, request

private_chat = Blueprint('private_chat', __name__, url_prefix='/chat/private')

@private_chat.route('')
def private():
    user = request.args.get('user')
    peer = request.args.get('peer')
    if not user or not peer:
        return "Missing user or peer", 400

    sorted_names = sorted([user, peer])
    room_id = f"private:{sorted_names[0]}:{sorted_names[1]}"
    ui_list_name = f"{sorted_names[0]}&{sorted_names[1]}"

    return render_template('chat.html',
                           ROOM_ID=room_id,
                           LIST_NAME=ui_list_name,
                           USERNAME=user)

