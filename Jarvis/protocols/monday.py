import datetime


def spec():
    return {
        "name": "monday",
        "aliases": ["shutdown jivan", "goodbye protocol"],
        "description": "Shutdown JIVAN protocol. When explicitly invoked, closes the JIVAN application (not the PC).",
        "side_effects": True,
        "confirmation_policy": "if_side_effects",
        "schedule": {"day_of_week": "monday"},
        "requires_confirmation": True,
        "triggers": [
            "run protocol monday",
            "execute protocol monday",
            "launch protocol monday",
            "monday protocol",
            "shutdown jivan",
            "monday",
        ],
        "negative_triggers": ["monday morning"],
        "cooldown_s": 3,
        "args_schema": {},
        "steps": [
            {"type": "action", "name": "shutdown_app"},
        ],
    }


def can_run(*, user_text, confirm=False):
    t = (user_text or "").lower()
    if "monday" in t and ("protocol" in t or t.strip() == "monday"):
        return True
    if "shutdown" in t and ("monday" in t):
        return True
    return bool(confirm)


def run(*, confirm=False):
    return {"ok": True, "action": "shutdown_app"}


def should_auto_run_today():
    return datetime.date.today().weekday() == 0
