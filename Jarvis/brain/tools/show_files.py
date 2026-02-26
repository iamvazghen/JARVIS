import os


def spec():
    return {
        "name": "show_files",
        "description": "Make hidden files visible in the current directory tree (side effect).",
        "args": {},
        "side_effects": True,
    }


def can_run(*, user_text):
    t = (user_text or "").lower()
    return ("make files visible" in t) or ("visible" in t)


def run(*, assistant=None, wolfram_fn=None):
    os.system("attrib -h /s /d")
    return True

