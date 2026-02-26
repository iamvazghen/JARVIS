def spec():
    return {
        "name": "news",
        "description": "Get top headlines (Times of India source).",
        "args": {},
    }


def run(*, assistant, wolfram_fn=None):
    articles = assistant.news()
    if not articles:
        return {"ok": False, "error_code": "no_news"}

    titles = []
    for a in articles[:10]:
        if isinstance(a, dict) and a.get("title"):
            titles.append(a["title"])
    return {"ok": True, "headlines": titles}
