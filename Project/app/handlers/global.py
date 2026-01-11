from flask import Blueprint, render_template, request

global_chat = Blueprint('global_chat', __name__, url_prefix='/chat/global')

@global_chat.route('')
def global_room():
    user = request.args.get('user', 'anonymous')
    room_id = "global:room"
    ui_list_name = "global_list"

    return render_template('chat.html',
                           ROOM_ID=room_id,
                           LIST_NAME=ui_list_name,
                           USERNAME=user)

