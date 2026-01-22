
import os

class BaseConfig:
    # --------------------
    # CORE
    # --------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DB_URI", "sqlite:///./dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SOCKETIO_MESSAGE_QUEUE = os.getenv("SOCKETIO_MESSAGE_QUEUE")

    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

    WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")

    FLUTTERWAVE_PUBLIC_KEY = os.getenv("FLUTTERWAVE_PUBLIC_KEY")
    FLUTTERWAVE_SECRET_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY")
    FLUTTERWAVE_WEBHOOK_SECRET = os.getenv("FLUTTERWAVE_WEBHOOK_SECRET")

    MONNIFY_API_KEY = os.getenv("MONNIFY_API_KEY")
    MONNIFY_SECRET_KEY = os.getenv("MONNIFY_SECRET_KEY")
    MONNIFY_CONTRACT_CODE = os.getenv("MONNIFY_CONTRACT_CODE")
    MONNIFY_BASE_URL = os.getenv(
        "MONNIFY_BASE_URL",
        "https://sandbox.monnify.com"
    )
    
    PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY")
    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
    PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET")

    PAYMENT_REDIRECT_URL = os.getenv(
        "PAYMENT_REDIRECT_URL",
        "http://localhost:3000/payment/callback"
    )

    MONNIFY_WALLET_LOAD_URL = os.getenv(
        "MONNIFY_WALLET_LOAD_URL",
        "/api/monnify/wallet/load"
    )

    PAYSTACK_WALLET_LOAD_URL = os.getenv(
        "PAYSTACK_WALLET_LOAD_URL",
        "/api/paystark/wallet/load"
    )

    FLUTTERWAVE_WALLET_LOAD_URL = os.getenv(
        "FLUTTERWAVE_WALLET_LOAD_URL",
        "/api/flutterwave/wallet/load"
    )


    WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v18.0")

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False

