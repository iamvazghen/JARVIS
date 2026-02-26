import pyautogui


def spec():
    return {
        "name": "take_screenshot",
        "description": "Take a screenshot and save it to a PNG file (side effect).",
        "args": {"filename": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, filename=""):
    t = (user_text or "").lower()
    return ("screenshot" in t) or ("capture screen" in t)


def run(*, assistant=None, wolfram_fn=None, filename="screenshot.png"):
    filename = (filename or "screenshot.png").strip()
    if not filename.lower().endswith(".png"):
        filename = filename + ".png"
    img = pyautogui.screenshot()
    img.save(filename)
    return filename

