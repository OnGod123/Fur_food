import asyncio
from hypercorn.asyncio import serve
from hypercorn.config import Config
from app import create_app
from app.extensions import socketio

"""
Development entry point.

This runs Flask (HTTP) + Socket.IO (WebSocket) on Hypercorn ASGI server.
"""

async def main():
    """ Create the Flask app + socketio """
    app, socketio_instance = create_app()

    """Convert Flask+SocketIO into an ASGI app"""
    asgi_app = socketio_instance.asgi_app

    """Hypercorn configuration """
    config = Config()
    config.bind = ["0.0.0.0:8000"]
    config.use_reloader = True    
    config.debug = True

    print("🚀 Starting development server on http://127.0.0.1:8000")
    print("⚡ WebSockets enabled through Socket.IO / ASGI / Hypercorn")

    # Run server
    await serve(asgi_app, config)


if __name__ == "__main__":
    asyncio.run(main())
