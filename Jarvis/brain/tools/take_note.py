def spec():
    return {
        "name": "take_note",
        "description": "Write a note to a text file and open it in an editor (side effect).",
        "args": {"text": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, text=""):
    t = (user_text or "").lower()
    return ("note" in t) or ("write this down" in t) or ("remember" in t)


def run(*, assistant, wolfram_fn=None, text=""):
    if not text:
        return False
    assistant.take_note(text)
    return True

