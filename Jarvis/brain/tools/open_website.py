import re


def spec():
    return {
        "name": "open_website",
        "description": "Open a website in the default browser (side effect).",
        "args": {"domain": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, domain=""):
    t = (user_text or "").lower()
    d = (domain or "").strip().lower()
    if not d:
        return False
    explicit_intent = (
        t.startswith("open ")
        or t.startswith("go to ")
        or t.startswith("visit ")
        or "open website" in t
        or "open browser" in t
    )
    if not explicit_intent:
        return False
    if d in t:
        return True
    if d.startswith("http://") or d.startswith("https://"):
        return True
    return bool(re.search(r"[a-z0-9-]+\.[a-z]{2,}", d))


def run(*, assistant, wolfram_fn=None, domain=""):
    return assistant.website_opener(domain)
