import random


_FAREWELLS = {
    "monday": [
        "It was a pleasure to be of your assistance. Goodbye.",
        "Always here when you need me. Shutting down now.",
        "Understood. Closing JIVAN. See you soon.",
    ],
    "monday_morning": [
        "It was a pleasure to be of your assistance. Shutting down the computer now.",
        "All set. Powering down the computer. See you soon.",
        "Understood. Initiating system shutdown. Take care.",
    ],
}


def pick(protocol_name: str) -> str:
    name = (protocol_name or "").strip().lower().replace(" ", "_")
    msgs = _FAREWELLS.get(name) or _FAREWELLS.get("monday") or ["Goodbye."]
    return random.choice(list(msgs))
