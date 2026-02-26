def spec():
    return {
        "name": "launch_app",
        "description": "Launch a local application by name (side effect).",
        "args": {"app": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, app=""):
    t = (user_text or "").lower()
    app = (app or "").strip().lower()
    if ("open app" in t) or ("open application" in t) or ("launch" in t) or ("start" in t):
        return True
    if "open" in t and app and app in t:
        return True
    return False


def run(*, assistant, wolfram_fn=None, app=""):
    app = (app or "").strip().lower()
    return assistant.launch_app_name(app, new_window=True)
