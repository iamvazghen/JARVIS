import json
import os


def _default_custom_dir():
    return os.path.join(os.path.dirname(__file__), "custom")


def _safe_name(name):
    t = str(name or "").strip().lower()
    if not t:
        return ""
    if any(ch in t for ch in ("/", "\\", ":", "*", "?", "\"", "<", ">", "|")):
        return ""
    return t


def _render_text(template, args, user_text):
    text = str(template or "")
    values = dict(args or {})
    values.setdefault("user_text", user_text or "")
    for k, v in values.items():
        token = "{{" + str(k) + "}}"
        text = text.replace(token, str(v))
    return text


class FileProtocol:
    def __init__(self, source_path, data):
        self._source_path = source_path
        self._data = dict(data or {})

    def spec(self):
        spec = dict(self._data)
        name = _safe_name(spec.get("name"))
        if not name:
            return {}
        spec["name"] = name
        spec.setdefault("aliases", [])
        spec.setdefault("description", f"Custom protocol loaded from {os.path.basename(self._source_path)}")
        spec.setdefault("side_effects", True)
        spec.setdefault("requires_confirmation", bool(spec.get("side_effects")))
        spec.setdefault("confirmation_policy", "if_side_effects")
        spec.setdefault("triggers", [])
        spec.setdefault("negative_triggers", [])
        spec.setdefault("args_schema", {})
        spec.setdefault("cooldown_s", 0)
        spec.setdefault("steps", [])
        spec["source"] = self._source_path
        return spec

    def build_steps(self, *, args=None, user_text=""):
        args = dict(args or {})
        steps = list((self._data or {}).get("steps") or [])
        rendered = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            item = dict(step)
            if "text" in item:
                item["text"] = _render_text(item.get("text"), args=args, user_text=user_text)
            if "name" in item:
                item["name"] = _render_text(item.get("name"), args=args, user_text=user_text)
            if "args" in item and isinstance(item.get("args"), dict):
                nested = {}
                for k, v in item.get("args").items():
                    nested[k] = _render_text(v, args=args, user_text=user_text) if isinstance(v, str) else v
                item["args"] = nested
            rendered.append(item)
        return rendered


def _load_one_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print(f"Custom protocol load failed ({path}): {e}")
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        print(f"Custom protocol file ignored ({path}): top-level must be object or list")
        return []

    protocols = []
    for item in data:
        if not isinstance(item, dict):
            continue
        proto = FileProtocol(path, item)
        if not proto.spec():
            print(f"Custom protocol ignored ({path}): invalid or missing name")
            continue
        protocols.append(proto)
    return protocols


def load_file_protocols(custom_dir=None):
    base = custom_dir or _default_custom_dir()
    if not os.path.isdir(base):
        return []

    modules = []
    for name in sorted(os.listdir(base)):
        if not name.lower().endswith(".json"):
            continue
        path = os.path.join(base, name)
        if not os.path.isfile(path):
            continue
        modules.extend(_load_one_json(path))
    return modules
