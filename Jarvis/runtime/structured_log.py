import datetime
import json
import os
import threading
import uuid

from Jarvis.config import config

_local = threading.local()


def set_turn_id(turn_id=None):
    _local.turn_id = str(turn_id or uuid.uuid4())
    return _local.turn_id


def get_turn_id():
    value = getattr(_local, "turn_id", "")
    return str(value or "")


def _path():
    p = getattr(config, "runtime_log_path", "Jarvis/data/runtime_events.jsonl")
    return os.path.abspath(str(p))


def log_event(event, **fields):
    row = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "event": str(event or ""),
        "turn_id": get_turn_id(),
    }
    row.update(fields or {})
    path = _path()
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        return False
    return True

