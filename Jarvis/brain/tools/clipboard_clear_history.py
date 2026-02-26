from . import clipboard_save


def spec():
    return {
        "name": "clipboard_clear_history",
        "description": "Clear the saved clipboard history for this session (side effect).",
        "args": {},
        "side_effects": True,
    }


def can_run(*, user_text):
    t = (user_text or "").lower()
    return ("clear" in t and "clipboard" in t) or ("reset" in t and "clipboard" in t)


def run(*, assistant=None, wolfram_fn=None):
    clipboard_save._HISTORY.clear()
    return True

