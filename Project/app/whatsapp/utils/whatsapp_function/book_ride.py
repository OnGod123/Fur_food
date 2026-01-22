def book_ride(self):
    session = self.session
    text = self.text
    phone = self.phone
    state = session.get("state")

    # -------------------- ASK_RIDE_PICKUP --------------------
    if state == "ASK_RIDE_PICKUP":
        result = ai_guard_step(
            step="ASK_RIDE_PICKUP",
            user_input=text,
            expected="Provide a real pickup location",
            examples=[
                "No 10 Allen Avenue, Ikeja, Lagos",
                "Shoprite Lekki Phase 1",
                "Unilag Main Gate, Akoka"
            ]
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        session["ride_pickup"] = result["value"]
        session["state"] = "ASK_RIDE_DESTINATION"
        self.save()
        self.send("➡️ Got it! Now, where should this ride go?")
        return "", 200

    # -------------------- ASK_RIDE_DESTINATION --------------------
    if state == "ASK_RIDE_DESTINATION":
        result = ai_guard_step(
            step="ASK_RIDE_DESTINATION",
            user_input=text,
            expected="Provide a real destination location",
            examples=[
                "No 12 Banana Island, Lagos",
                "Lekki Phase 1, Shoprite",
                "Ojota Bus Stop, Lagos"
            ]
        )
        if not result["ok"]:
            self.send(result["hint"])
            return "", 200

        session["ride_destination"] = result["value"]
        session["state"] = "CONFIRM_RIDE"
        self.save()
        self.send(
            f"✅ Pickup: {session['ride_pickup']}\n"
            f"✅ Destination: {session['ride_destination']}\n\n"
            "Reply YES to confirm and proceed with payment."
        )
        return "", 200

    # ---------- Default return ----------
    return "", 200

