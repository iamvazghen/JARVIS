import subprocess


def spec():
    return {
        "name": "focus_mode",
        "description": "Optional focus-mode helper (can close common distraction apps). Requires confirm to take action.",
        "args": {"close_apps": "boolean", "confirm": "boolean"},
        "side_effects": True,
    }


def can_run(*, user_text, close_apps=False, confirm=False):
    t = (user_text or "").lower()
    return ("focus mode" in t) or ("enable focus" in t) or bool(confirm)


def run(*, assistant=None, wolfram_fn=None, close_apps=False, confirm=False):
    if not confirm:
        return {"ok": False, "error_code": "confirmation_required"}

    actions = []
    errors = []
    if close_apps:
        for exe in ["chrome.exe", "Discord.exe", "Teams.exe", "slack.exe", "Spotify.exe"]:
            proc = subprocess.run(
                ["taskkill", "/f", "/im", exe],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                actions.append(f"closed:{exe}")
            else:
                errors.append({"app": exe, "error": (proc.stderr or "").strip()})

    return {
        "ok": True,
        "actions": actions or ["no-op"],
        "errors": errors[:25],
        "error_count": len(errors),
    }
