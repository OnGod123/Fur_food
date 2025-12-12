from flask import Flask
from app.config import DevelopmentConfig, ProductionConfig
from app.extensions import init_db, socketio, init_redis, init_minio
from app.extensions import SessionLocal

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
    
    init_redis(app)
    init_minio(app)
    init_db(app)

    """initialize socketio with ASGI mode"""
    """note: we still call socketio.init_app so decorators work; we'll create an ASGIApp for Hypercorn"""
    socketio.init_app(app, async_mode= "eventlet", message_queue=app.config.get("SOCKETIO_MESSAGE_QUEUE"))
    from app.handlers.home import home_bp
    app.register_blueprint(home_bp)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Ensure SQLAlchemy sessions are cleaned up per request."""
        SessionLocal.remove()



    return app, socketio
