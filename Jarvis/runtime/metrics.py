import json
import os
import time

from Jarvis.config import config

_COUNTERS = {}
_LAT_MS = {}


def metrics_inc(name, value=1):
    key = str(name or "")
    if not key:
        return
    _COUNTERS[key] = int(_COUNTERS.get(key, 0)) + int(value)


def metrics_observe_ms(name, value_ms):
    key = str(name or "")
    if not key:
        return
    arr = _LAT_MS.get(key) or []
    arr.append(float(value_ms))
    if len(arr) > 200:
        arr = arr[-200:]
    _LAT_MS[key] = arr


def metrics_snapshot():
    out = {"counters": dict(_COUNTERS), "latency_ms": {}}
    for k, vals in _LAT_MS.items():
        if not vals:
            continue
        out["latency_ms"][k] = {
            "count": len(vals),
            "avg": sum(vals) / float(len(vals)),
            "p95": sorted(vals)[max(0, int(len(vals) * 0.95) - 1)],
        }
    out["ts_epoch"] = int(time.time())
    path = os.path.abspath(str(getattr(config, "runtime_metrics_path", "Jarvis/data/metrics_snapshot.json")))
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return out

