import pyperclip


_HISTORY = []
_MAX = 25


def spec():
    return {
        "name": "clipboard_save",
        "description": "Save current clipboard text into an in-memory history for this session.",
        "args": {},
        "side_effects": True,
    }


def can_run(*, user_text):
    t = (user_text or "").lower()
    return ("save" in t and "clipboard" in t) or ("remember" in t and "clipboard" in t)


def run(*, assistant=None, wolfram_fn=None):
    try:
        text = pyperclip.paste()
    except Exception:
        text = ""

    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "Clipboard is empty."}

    _HISTORY.insert(0, text)
    del _HISTORY[_MAX:]
    return {"ok": True, "count": len(_HISTORY)}


def _history():
    return list(_HISTORY)

