import json
from pathlib import Path


_PATH = Path.cwd() / "contacts.json"


def spec():
    return {
        "name": "contacts_manage",
        "description": "Manage a simple contacts book stored in contacts.json (side effect for writes).",
        "args": {"action": "string", "name": "string", "email": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, action="", name="", email=""):
    t = (user_text or "").lower()
    return ("contact" in t) or ("address book" in t) or ("email" in t)


def _load():
    if not _PATH.exists():
        return {}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _save(data):
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run(*, assistant=None, wolfram_fn=None, action="list", name="", email=""):
    data = _load()
    action = (action or "list").strip().lower()

    if action == "list":
        return [{"name": k, "email": v} for k, v in sorted(data.items())]

    if action == "get":
        return data.get((name or "").strip(), None)

    if action == "add":
        n = (name or "").strip()
        e = (email or "").strip()
        if not n or not e:
            return {"ok": False, "error": "name and email are required"}
        data[n] = e
        _save(data)
        return {"ok": True}

    if action == "remove":
        n = (name or "").strip()
        if n in data:
            data.pop(n, None)
            _save(data)
            return {"ok": True}
        return {"ok": False, "error": "not found"}

    return {"ok": False, "error": "unknown action"}

