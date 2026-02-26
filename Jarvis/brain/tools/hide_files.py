import os


def spec():
    return {
        "name": "hide_files",
        "description": "Hide all files in the current directory tree (side effect).",
        "args": {},
        "side_effects": True,
    }


def can_run(*, user_text):
    t = (user_text or "").lower()
    return ("hide all files" in t) or ("hide this folder" in t)


def run(*, assistant=None, wolfram_fn=None):
    os.system("attrib +h /s /d")
    return True

