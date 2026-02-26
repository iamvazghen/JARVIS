import datetime
import json
import os

from Jarvis.config import config
from .structured_log import get_turn_id


def _path():
    p = getattr(config, "runtime_receipts_path", "Jarvis/data/delivery_receipts.jsonl")
    return os.path.abspath(str(p))


def record_receipt(channel, action, ok, details=None):
    row = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "turn_id": get_turn_id(),
        "channel": str(channel or ""),
        "action": str(action or ""),
        "ok": bool(ok),
        "details": details if isinstance(details, dict) else {"text": str(details or "")},
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


def recent_receipts(limit=20):
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
    return rows[-max(1, int(limit)) :]

