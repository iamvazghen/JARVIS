import json

from Jarvis import JarvisAssistant
from Jarvis.brain import JarvisBrain


def main():
    assistant = JarvisAssistant()
    brain = JarvisBrain(assistant=assistant, wolfram_fn=lambda q: None)
    report = {
        "mem0": brain.mem0_health(force=True),
        "mcp": brain.mcp_health(force=True),
        "redis": brain.redis_health(force=True),
    }
    checks = [
        ("TELEGRAM_GET_ME", {}),
        ("GMAIL_GET_PROFILE", {}),
        ("GIPHY_TRENDING_GIFS", {"limit": 1}),
    ]
    from Jarvis.brain.mcp import ComposioMCPClient

    cli = ComposioMCPClient()
    live = []
    for name, args in checks:
        r = cli.execute(tool_name=name, tool_input=args)
        live.append({"tool": name, "ok": bool(r.get("ok")), "error_code": r.get("error_code", "")})
    report["live_tools"] = live
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

