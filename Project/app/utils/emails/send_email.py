import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def send_email_notification(email: str, notif_dict: dict):
    """
    Parameters MUST match:
    send_email_notification.delay(vendor.email, notif_dict)
    """

    subject = "New Order Notification"

    body = f"""
Hello,

You have received a new order.

Order ID: {notif_dict.get('order_id')}
Type: {notif_dict.get('type')}

Please log in to your dashboard to process the order.

Thank you.
"""

    msg = MIMEMultipart()
    msg["From"] = current_app.config["SMTP_FROM_EMAIL"]
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(
            current_app.config["SMTP_HOST"],
            current_app.config.get("SMTP_PORT", 587),
        ) as server:
            server.starttls()
            server.login(
                current_app.config["SMTP_USERNAME"],
                current_app.config["SMTP_PASSWORD"],
            )
            server.sendmail(
                msg["From"],
                [email],
                msg.as_string(),
            )

    except Exception:
        current_app.logger.exception("Email send failed")
        raise

