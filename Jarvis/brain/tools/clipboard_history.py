from . import clipboard_save


def spec():
    return {
        "name": "clipboard_history",
        "description": "List saved clipboard entries for this session.",
        "args": {"limit": "number"},
    }


def run(*, assistant=None, wolfram_fn=None, limit=10):
    try:
        limit = int(limit)
    except Exception:
        limit = 10
    limit = max(1, min(25, limit))

    items = clipboard_save._history()[:limit]
    return [{"index": i, "text": t} for i, t in enumerate(items)]

