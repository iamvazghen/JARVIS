import os
import re

from Jarvis.config import config


def scan_env_secrets():
    if str(getattr(config, "runtime_secrets_scan", "1")).lower() not in ("1", "true", "yes", "on"):
        return {"ok": True, "warnings": []}
    warnings = []
    for k, v in os.environ.items():
        key = str(k)
        val = str(v or "")
        if not val:
            continue
        if any(s in key.upper() for s in ("KEY", "TOKEN", "PASSWORD", "SECRET")):
            if "changeme" in val.lower() or "your-" in val.lower():
                warnings.append({"code": "placeholder_secret", "env": key})
            if len(val) < 8:
                warnings.append({"code": "short_secret", "env": key})
            if re.search(r"\s", val):
                warnings.append({"code": "whitespace_secret", "env": key})
    return {"ok": True, "warnings": warnings}

