from flask import Flask
from app.config import DevelopmentConfig
from app.extensions import init_db, socketio, init_redis, init_minio, SessionLocal, oauth, init_redis

def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=False)

    if config_object is None:
        config_object = DevelopmentConfig
    app.config.from_object(config_object)

    init_redis(app)
    init_minio(app)
    init_db(app)
    oauth.init_app(app)
    

    
    socketio.init_app(app, message_queue=app.config.get("SOCKETIO_MESSAGE_QUEUE"))

    from app.handlers.home import home_bp
    from app.handlers.Google_login import auth_bp
    from app.handlers.phone_login import auth_bp_phone
    from app.handlers.login_as_guest import loginas_guest_bp
    from app.handlers.signup import signup_bp
    from app.handlers.dashboard import dashboard
    from app.handlers.payment_handler import wallet_payment_bp


    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(auth_bp_phone)
    app.register_blueprint(loginas_guest_bp)
    app.register_blueprint(signup_bp)
    app.register_blueprint(dashboard)
    app.register_blueprint(wallet_payment_bp)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if SessionLocal:
            SessionLocal.remove()


    return app, socketio

