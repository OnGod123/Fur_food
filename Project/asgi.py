from app import create_app
from app.extensions import socketio
import eventlet

eventlet.monkey_patch()

app, socketio_instance = create_app()

if __name__ == "__main__":
    print("🚀 Running dev server on http://0.0.0.0:5000")
    socketio_instance.run(app, host="0.0.0.0", port=5000, debug=True)
