import pyperclip


def spec():
    return {
        "name": "clipboard_get",
        "description": "Read the current clipboard text.",
        "args": {},
    }


def run(*, assistant=None, wolfram_fn=None):
    try:
        return pyperclip.paste()
    except Exception:
        return ""

