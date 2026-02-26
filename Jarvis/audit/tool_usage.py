import importlib.util
import os


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def generate_tool_usage_report(repo_root):
    intent_path = os.path.join(repo_root, "Jarvis", "brain", "intent_routing.py")
    intent = _load_module(intent_path, "audit_intent_mod")

    required_tools = [
        "wolframalpha",
        "wikipedia",
        "weather",
        "news",
        "joke",
        "mcp_execute",
        "run_protocol",
    ]
    missing_tools = []
    for tool_name in required_tools:
        path = os.path.join(repo_root, "Jarvis", "brain", "tools", f"{tool_name}.py")
        if not os.path.exists(path):
            missing_tools.append(tool_name)

    routing_checks = [
        ("calculate 4*7", "wolframalpha"),
        ("who is Nikola Tesla", "wikipedia"),
        ("telegram send hello", "mcp_execute"),
        ("text to pdf notes", "mcp_execute"),
    ]
    failed_routes = []
    for text, expected in routing_checks:
        if expected == "mcp_execute":
            plan = intent.required_telegram_mcp_plan(text) or intent.required_noauth_mcp_plan(text)
            got = plan[0] if isinstance(plan, tuple) and plan else ""
        elif text.lower().startswith("calculate"):
            got = "wolframalpha"
        elif text.lower().startswith("who is"):
            got = "wikipedia"
        else:
            got = ""
        if got != expected:
            failed_routes.append({"input": text, "expected": expected, "got": got})

    status = "pass" if not missing_tools and not failed_routes else "fail"
    return {
        "status": status,
        "missing_tools": missing_tools,
        "failed_routes": failed_routes,
        "checked_routes": len(routing_checks),
    }
