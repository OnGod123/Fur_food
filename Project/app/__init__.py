from flask import Flask
from app.config import DevelopmentConfig
from app.extensions import init_db, socketio, init_redis, init_minio, SessionLocal, oauth

def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=False)

    if config_object is None:
        config_object = DevelopmentConfig
    app.config.from_object(config_object)

    init_redis(app)
    init_minio(app)
    init_db(app)
    oauth.init_app(app)

    # Remove async_mode="asgi" → Eventlet will handle async internally
    socketio.init_app(app, message_queue=app.config.get("SOCKETIO_MESSAGE_QUEUE"))

    from app.handlers.home import home_bp
    app.register_blueprint(home_bp)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        SessionLocal.remove()

    return app, socketio

