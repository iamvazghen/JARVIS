import datetime
import json
import os

from Jarvis.config import config
from .structured_log import get_turn_id


def _path():
    p = getattr(config, "runtime_replay_path", "Jarvis/data/conversation_replay.jsonl")
    return os.path.abspath(str(p))


def replay_event(stage, payload):
    row = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "turn_id": get_turn_id(),
        "stage": str(stage or ""),
        "payload": payload if isinstance(payload, dict) else {"value": str(payload or "")},
    }
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

