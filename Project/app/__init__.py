from flask import Flask
from app.config import DevelopmentConfig, ProductionConfig
from app.extensions import db, socketio, init_redis, init_minio

def create_app(config_object=None):
    """
    Returns (flask_app, socketio_instance_or_None)
    """
    app = Flask(__name__, instance_relative_config=False)

    # pick config
    if config_object is None:
        config_object = DevelopmentConfig
    app.config.from_object(config_object)

    """ init extensions that use the app"""
    db.init_app(app)
    init_redis(app)
    init_minio(app)

    """initialize socketio with ASGI mode"""
    """note: we still call socketio.init_app so decorators work; we'll create an ASGIApp for Hypercorn"""
    socketio.init_app(app, async_mode="asgi", message_queue=app.config.get("SOCKETIO_MESSAGE_QUEUE"))
    from app.handlers.home import home_bp
    app.register_blueprint(home_bp)


    return app, socketio
