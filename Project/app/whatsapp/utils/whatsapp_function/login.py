def login(self):
    session = self.session
    text = self.text
    state = session.get("state")

    # ---- ENTRY POINT ----
    if not state:
        session["state"] = "NEW_USER_FIRST_NAME"
        self.save()
        self.send(
            "👋 Welcome! Let's get you started.\n"
            "Please enter your *first name*:"
        )
        return

    # ---- FIRST NAME ----
    if state == "NEW_USER_FIRST_NAME":
        result = ai_guard_step(
            step="FIRST_NAME",
            user_input=text,
            expected="Send your first name",
            examples=["John", "Aisha", "Samuel"],
        )
        if not result["ok"]:
            self.send(result["hint"])
            return

        session["first_name"] = result["value"]
        session["state"] = "NEW_USER_LAST_NAME"
        self.save()
        self.send("➡️ Great! Now enter your *surname*:")
        return

    # ---- LAST NAME ----
    if state == "NEW_USER_LAST_NAME":
        result = ai_guard_step(
            step="LAST_NAME",
            user_input=text,
            expected="Send your surname",
            examples=["Doe", "Okafor", "Balogun"],
        )
        if not result["ok"]:
            self.send(result["hint"])
            return

        session["last_name"] = result["value"]
        session["state"] = "NEW_USER_ACCOUNT"
        self.save()
        self.send("➡️ Enter your *bank account number*:")
        return

    # ---- ACCOUNT NUMBER ----
    if state == "NEW_USER_ACCOUNT":
        result = ai_guard_step(
            step="ACCOUNT_NUMBER",
            user_input=text,
            expected="Send a valid bank account number",
            examples=["0123456789"],
        )
        if not result["ok"]:
            self.send(result["hint"])
            return

        session["account_number"] = result["value"]
        session["state"] = "NEW_USER_PASSWORD"
        self.save()
        self.send("🔐 Create a *password* (min 6 chars):")
        return

    # ---- PASSWORD ----
    if state == "NEW_USER_PASSWORD":
        result = ai_guard_step(
            step="PASSWORD",
            user_input=text,
            expected="Create a secure password",
            examples=["mypassword123"],
        )
        if not result["ok"]:
            self.send(result["hint"])
            return

        session["password"] = result["value"]
        session["state"] = "NEW_USER_CONFIRM_PASSWORD"
        self.save()
        self.send("🔁 Confirm your password:")
        return

    # ---- CONFIRM PASSWORD ----
    if state == "NEW_USER_CONFIRM_PASSWORD":
        if text != session.get("password"):
            self.send("❌ Passwords do not match. Try again.")
            session["state"] = "NEW_USER_PASSWORD"
            self.save()
            return

        # ✅ CREATE USER
        user = create_user(
            first_name=session["first_name"],
            last_name=session["last_name"],
            account_number=session["account_number"],
            password=session["password"],  # hash in prod
            phone=self.phone,
        )

        session["registered"] = True
        session["user_id"] = user.id
        session["state"] = "MENU"
        self.save()

        self.send("✅ Registration complete!\n\n" + MENU_TEXT)
        return

