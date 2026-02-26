import urllib.parse
import webbrowser


def spec():
    return {
        "name": "web_search",
        "description": "Open a web search in the default browser (side effect).",
        "args": {"query": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, query=""):
    t = (user_text or "").lower()
    return ("search" in t) or ("look up" in t) or ("google" in t)


def run(*, assistant=None, wolfram_fn=None, query=""):
    q = (query or "").strip()
    if not q:
        return False
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(q)
    webbrowser.open(url)
    return True

