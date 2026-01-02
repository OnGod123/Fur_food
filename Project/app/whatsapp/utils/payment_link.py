def build_payment_link(provider_name: str | None = None) -> str:
    """
    Build the /wallet/callback URL.
    If provider_name is provided, append it to the path.
    """
    base_url = "/wallet/callback"
    if provider_name:
        return f"{base_url}/{provider_name.lower()}"
    return base_url


