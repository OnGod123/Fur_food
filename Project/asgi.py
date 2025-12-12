
import asyncio
from hypercorn.asyncio import serve
from hypercorn.config import Config
from app import create_app
from flask_socketio import SocketIO

if __name__ == "__main__":
    app, socketio = create_app()
    asgi_app = socketio.ASGIApp(app)
    config = Config()
    config.bind = ["0.0.0.0:8000"]
    asyncio.run(serve(asgi_app, config))
