import pyperclip


def spec():
    return {
        "name": "clipboard_set",
        "description": "Set clipboard text (side effect).",
        "args": {"text": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, text=""):
    t = (user_text or "").lower()
    return ("copy" in t) or ("clipboard" in t) or ("paste" in t)


def run(*, assistant=None, wolfram_fn=None, text=""):
    pyperclip.copy(text or "")
    return True

