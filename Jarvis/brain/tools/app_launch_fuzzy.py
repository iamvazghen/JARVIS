import os


def spec():
    return {
        "name": "app_launch_fuzzy",
        "description": "Launch a known application by name (limited mapping) or explicit path (side effect).",
        "args": {"app": "string", "path": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, app="", path=""):
    t = (user_text or "").lower()
    app = (app or "").strip().lower()
    if ("open app" in t) or ("open application" in t) or ("launch" in t) or ("start" in t):
        return True
    if "open" in t and app and app in t:
        return True
    return False


def run(*, assistant=None, wolfram_fn=None, app="", path=""):
    path = (path or "").strip()
    if path:
        if os.path.exists(path):
            os.startfile(path)
            return True
        return False

    app = (app or "").strip().lower()
    if assistant:
        return assistant.launch_app_name(app, new_window=True)
    return False
