import requests

from Jarvis.runtime.secrets import scan_env_secrets


def startup_precheck(*, assistant=None, brain=None):
    out = {"mic": False, "internet": False, "mem0": "unknown", "mcp": "unknown", "redis": "unknown", "warnings": []}
    try:
        out["mic"] = bool(assistant and assistant.mic_available())
    except Exception:
        out["mic"] = False
    try:
        r = requests.get("https://api.ipify.org", timeout=3)
        out["internet"] = bool(r.ok and r.text)
    except Exception:
        out["internet"] = False
    if brain is not None:
        try:
            m = brain.mem0_health(force=True)
            out["mem0"] = m.get("status", "unknown")
        except Exception:
            out["mem0"] = "error"
        try:
            m = brain.mcp_health(force=True)
            out["mcp"] = m.get("status", "unknown")
        except Exception:
            out["mcp"] = "error"
        try:
            m = brain.redis_health(force=True)
            out["redis"] = m.get("status", "unknown")
        except Exception:
            out["redis"] = "error"
    sec = scan_env_secrets()
    out["warnings"].extend(sec.get("warnings", []))
    return out

