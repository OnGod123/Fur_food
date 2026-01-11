
def ensure_locatable(text):
    return ai_guard_step(
        step="LOCATABLE_ADDRESS",
        user_input=text,
        expected="A real, locatable place or address",
        examples=[
            "No 10 Allen Avenue, Ikeja, Lagos",
            "Shoprite Lekki Phase 1",
            "Unilag Main Gate, Akoka",
            "Ojota Bus Stop, Lagos",
        ],
    )

