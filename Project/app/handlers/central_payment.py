from flask import Blueprint, redirect, current_app
from app.utils.jwt_tokens.guest_token import check_if_guest

wallet_bp = Blueprint("wallet_bp", __name__)

@wallet_bp.route("/wallet/callback/<provider_name>", methods=["GET"])
@check_if_guest
def wallet_callback(provider_name):
    """
    Redirects to the provider-specific wallet load page.
    """

    if provider_name == "monnify":
        return redirect(current_app.config["MONNIFY_WALLET_LOAD_URL"])

    elif provider_name == "paystack":
        return redirect(current_app.config["PAYSTACK_WALLET_LOAD_URL"])

    elif provider_name == "flutterwave":
        return redirect(current_app.config["FLUTTERWAVE_WALLET_LOAD_URL"])

    return redirect(current_app.config["PAYSTACK_WALLET_LOAD_URL"])

