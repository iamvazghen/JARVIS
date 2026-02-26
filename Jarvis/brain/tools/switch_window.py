import pyautogui
import time


def spec():
    return {
        "name": "switch_window",
        "description": "Alt+Tab to switch windows (side effect).",
        "args": {},
        "side_effects": True,
    }


def can_run(*, user_text):
    t = (user_text or "").lower()
    return ("switch window" in t) or ("switch the window" in t) or ("alt tab" in t)


def run(*, assistant=None, wolfram_fn=None):
    pyautogui.keyDown("alt")
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.keyUp("alt")
    return True

