def build_bargain_slug(user1: str, user2: str) -> str:
    """
    Generates a deterministic URL-safe slug for a private bargain chat.

    Example:
        ben + mrbiggs     → ben__mrbiggs
        mrbiggs + ben     → ben__mrbiggs
    """
    users = sorted([
        user1.strip().lower(),
        user2.strip().lower()
    ])

    return f"{users[0]}__{users[1]}"



def build_bargain_url(user1: str, user2: str) -> str:
    slug = build_bargain_slug(user1, user2)
    return f"/bargain/{slug}"



@bargain_bp.route("/bargain/<slug>")
def bargain_chat(slug):
    user1, user2 = parse_bargain_slug(slug)

    if not user1 or not user2:
        abort(404)

    return render_template(
        "bargain.html",
        user1=user1,
        user2=user2,
        room=slug
    )

