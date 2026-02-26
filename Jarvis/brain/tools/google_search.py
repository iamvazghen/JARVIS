def spec():
    return {
        "name": "google_search",
        "description": "Search Google for a query using the project's Selenium/ChromeDriver flow (side effect).",
        "args": {"query": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, query=""):
    t = (user_text or "").lower()
    q = (query or "").strip()
    if not q:
        return False
    return (
        ("search google for" in t)
        or ("google search for" in t)
        or ("look up on google" in t)
        or ("search for" in t and "google" in t)
    )


def run(*, assistant, wolfram_fn=None, query=""):
    query = (query or "").strip()
    if not query:
        return False
    assistant.search_anything_google(f"search google for {query}")
    return True
