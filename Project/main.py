import eventlet
eventlet.monkey_patch()
from app import create_app
from app.extensions import socketio


app, socketio_instance = create_app()

if __name__ == "__main__":
    print("🚀 Starting Flask + SocketIO server on http://0.0.0.0:5000")
    # Eventlet handles HTTP + WebSocket in the same process
    socketio_instance.run(app, host="0.0.0.0", port=5000)

