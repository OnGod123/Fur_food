from openai import OpenAI
from flask import current_app

client = OpenAI(api_key=current_app.config["OPENAI_API_KEY"])


def ai_guard_step(step, user_input, expected, examples=None):
    """
    AI validator + guide for each WhatsApp step.

    Args:
        step (str): Current flow step (MENU, ASK_VENDOR, ASK_ITEMS, ASK_ADDRESS, etc.)
        user_input (str): Raw user message
        expected (str): What is expected at this step
        examples (list): Optional examples of correct input

    Returns:
        dict:
            {
              "ok": bool,
              "value": cleaned_or_interpreted_value,
              "hint": message_to_user_if_invalid
            }
    """

    example_text = ""
    if examples:
        example_text = "\nExamples:\n" + "\n".join(f"- {e}" for e in examples)

    system_prompt = f"""
You are an intelligent WhatsApp assistant helping users complete tasks step by step.

Current step: {step}

What the user should do now:
{expected}

Rules:
- If the user's input correctly satisfies this step, return JSON:
  {{ "ok": true, "value": "<cleaned value>" }}

- If incorrect or unclear, return JSON:
  {{
    "ok": false,
    "value": null,
    "hint": "<clear friendly explanation of what to do>"
  }}

- Do NOT include any text outside JSON.
- Be concise and friendly.
{example_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": step},
            {"role": "system", "content": expected},
            {"role": "system", "content":examples}
            {"role": "user", "content": user_input}
            
        ],
    )

    return eval(response.choices[0].message.content)


result = ai_guard_step(
    step="MENU",
    user_input=text,
    expected="Choose one of: ORDER, WALLET, TRACK, ERRAND, RIDE",
    examples=[
        "Order food",
        "Fund wallet",
        "Track my delivery",
        "Send an errand",
        "Request a ride",
    ],
)


result = ai_guard_step(
    step="ASK_VENDOR",
    user_input=text,
    expected="Enter the name of the food vendor",
    examples=["Jamborine", "Chicken Republic", "Mr Biggs"],
)


result = ai_guard_step(
    step="ASK_ITEMS",
    user_input=text,
    expected="Select an item number from the menu OR describe a custom order",
    examples=["1", "2", "I want rice and chicken"],
)


result = ai_guard_step(
    step="ASK_ADDRESS",
    user_input=text,
    expected="Send a clear delivery address someone can find",
    examples=[
        "12 Allen Avenue Ikeja",
        "Opposite Shoprite Lekki Phase 1",
    ],
)

result = ai_guard_step(
    step="CONFIRM",
    user_input=text,
    expected="Confirm the order by saying YES or cancel by saying NO",
    examples=["Yes", "Confirm", "No", "Cancel"],
)

result = ai_guard_step(
    step="ASK_QUANTITY",
    user_input=text,
    expected="Enter a valid quantity (positive number)",
    examples=["1", "2", "3", "5", "10"],
)

result = ai_guard_step(
    step="ASK_ERRAND",
    user_input=text,
    expected=(
        "Describe the errand clearly. "
        "Include what to do, where to go, and any important detail."
    ),
    examples=[
        "Pick up documents from Ikeja and deliver to Lekki",
        "Buy groceries from Shoprite Yaba",
        "Deliver a package to No 10 Allen Avenue",
    ],
)


result = ai_guard_step(
    step="ASK_RIDE_PICKUP",
    user_input=text,
    expected="Enter your pickup location clearly",
    examples=[
        "Ikeja Along Allen Avenue",
        "Unilag Main Gate",
        "Shoprite Lekki Phase 1",
    ],
)

result = ai_guard_step(
    step="ASK_RIDE_DESTINATION",
    user_input=text,
    expected="Enter where you are going",
    examples=[
        "Lekki Phase 1",
        "Yaba Bus Stop",
        "Ajah",
    ],
)

result = ai_guard_step(
    step="TRACK",
    user_input=text,
    expected="Send the delivery or tracking ID you received",
    examples=[
        "DEL-102938",
        "ORDER-8891",
        "123456",
    ],
)

result = ai_guard_step(
    step="SET_LOCATION",
    user_input=text,
    expected="Set or update your current location",
    examples=[
        "SET LOCATION: Ikeja Along Allen Avenue, Lagos",
        "UPDATE LOCATION: Shoprite Lekki Phase 1"
    ],
)

result = ai_guard_step(
    step="LOCATABLE_ADDRESS",
    user_input=text,
    expected="A real, locatable place or address",
    examples=[
        "No 10 Allen Avenue, Ikeja, Lagos",
        "Shoprite Lekki Phase 1",
        "Unilag Main Gate, Akoka",
        "Ojota Bus Stop, Lagos"
    ],
)
result = ai_guard_step(
        step="ASK_ERRAND",
        user_input=text,
        expected="Describe the errand clearly, include pickup and destination",
        examples=[
            "Pick up documents from Ikeja and deliver to Lekki",
            "Buy groceries from Shoprite Yaba and deliver to my home",
        ],
    )
