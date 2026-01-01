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


def send_welcome_email(email: str, username: str):
    """
    Sends a welcome email in HTML format to a rider after successful login.
    """
    subject = "Welcome to Fur Food! 🚴‍♂️"

    # HTML email template
    html_body = f"""
    <html>
    <body>
        <div style="font-family: Arial, sans-serif; line-height: 1.5; color: #333;">
            <h2 style="color: #FF6F61;">Welcome, {username}!</h2>
            <p>Thank you for joining Fur Food as a rider.</p>
            <p>You can now start accepting delivery requests and earn with every ride!</p>
            <p>
                <a href="https://yourfrontenddomain.com/rider/delivery"
                   style="background-color: #FF6F61; color: white; padding: 10px 20px;
                          text-decoration: none; border-radius: 5px;">
                   Go to Delivery Page
                </a>
            </p>
            <hr>
            <p style="font-size: 12px; color: #777;">
                Fur Food Team<br>
                Delivering happiness to your doorstep!
            </p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = current_app.config["SMTP_FROM_EMAIL"]
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

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
            server.sendmail(msg["From"], [email], msg.as_string())

    except Exception as e:
        current_app.logger.exception("Welcome email send failed")
        raise e

