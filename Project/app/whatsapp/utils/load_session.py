def load_session(phone: str) -> dict:
    key = f"whatsapp:session:{phone}"

    if not r.exists(key):
        return {"state": "MENU"}

    raw = r.hgetall(key)
    session = {}

    for k, v in raw.items():
        try:
            session[k] = json.loads(v)
        except Exception:
            session[k] = v

    return session




def save_session(phone: str, session: dict):
    key = f"whatsapp:session:{phone}"

    # Redis hashes only accept strings
    safe_session = {}

    for k, v in session.items():
        if isinstance(v, (dict, list)):
            safe_session[k] = json.dumps(v)
        else:
            safe_session[k] = str(v)

    r.hset(key, mapping=safe_session)
    r.expire(key, 60 * 30)  # 30 minutes timeout




