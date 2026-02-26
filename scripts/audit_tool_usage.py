import json
import os
import importlib.util

def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    mod = _load(os.path.join(root, "Jarvis", "audit", "tool_usage.py"), "audit_tool_usage_mod")
    report = mod.generate_tool_usage_report(root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
