import datetime
import hashlib
import json
import os

from Jarvis.config import config


def _path():
    p = getattr(config, "runtime_outbound_queue_path", "Jarvis/data/outbound_queue.jsonl")
    return os.path.abspath(str(p))


def _key(channel, action, payload):
    raw = json.dumps({"c": channel, "a": action, "p": payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def enqueue(channel, action, payload):
    row = {
        "id": _key(channel, action, payload),
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "channel": str(channel or ""),
        "action": str(action or ""),
        "payload": payload if isinstance(payload, dict) else {},
        "attempts": 0,
    }
    items = load_pending()
    if any(x.get("id") == row["id"] for x in items):
        return row["id"], False
    items.append(row)
    _save(items)
    return row["id"], True


def load_pending():
    path = _path()
    if not os.path.exists(path):
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except Exception:
        return []
    return rows


def _save(rows):
    path = _path()
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def remove(item_id):
    rows = [x for x in load_pending() if str(x.get("id")) != str(item_id)]
    _save(rows)

