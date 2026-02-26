from pathlib import Path
import datetime


_PATH = Path.cwd() / "todo.md"


def spec():
    return {
        "name": "todo_manage",
        "description": "Manage a simple Markdown todo list in todo.md (side effect).",
        "args": {"action": "string", "text": "string", "index": "number"},
        "side_effects": True,
    }


def can_run(*, user_text, action="", text="", index=None):
    t = (user_text or "").lower()
    return ("todo" in t) or ("task" in t)


def _read_lines():
    if not _PATH.exists():
        return []
    return _PATH.read_text(encoding="utf-8").splitlines()


def _write_lines(lines):
    _PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(*, assistant=None, wolfram_fn=None, action="list", text="", index=None):
    action = (action or "list").strip().lower()
    lines = _read_lines()

    tasks = [l for l in lines if l.strip().startswith("- [")]

    if action == "list":
        return [{"index": i, "task": t} for i, t in enumerate(tasks)]

    if action == "add":
        t = (text or "").strip()
        if not t:
            return {"ok": False, "error": "text required"}
        stamp = datetime.date.today().isoformat()
        lines.append(f"- [ ] {t} ({stamp})")
        _write_lines(lines)
        return {"ok": True}

    if action == "done":
        try:
            idx = int(index)
        except Exception:
            return {"ok": False, "error": "index required"}
        if idx < 0 or idx >= len(tasks):
            return {"ok": False, "error": "index out of range"}
        target = tasks[idx]
        new_lines = []
        replaced = False
        for l in lines:
            if not replaced and l == target:
                new_lines.append(l.replace("- [ ]", "- [x]", 1))
                replaced = True
            else:
                new_lines.append(l)
        _write_lines(new_lines)
        return {"ok": True}

    return {"ok": False, "error": "unknown action"}

