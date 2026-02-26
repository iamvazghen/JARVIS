import datetime


def spec():
    return {
        "name": "monday_morning",
        "aliases": ["monday morning"],
        "description": "Shutdown PC protocol for Monday morning. When explicitly invoked, shuts down the computer.",
        "side_effects": True,
        "confirmation_policy": "if_side_effects",
        "schedule": {"day_of_week": "monday", "time_hint": "morning"},
        "requires_confirmation": True,
        "triggers": [
            "run protocol monday morning",
            "execute protocol monday morning",
            "launch protocol monday morning",
            "monday morning protocol",
            "shutdown monday morning",
        ],
        "cooldown_s": 3,
        "args_schema": {},
        "steps": [
            {"type": "action", "name": "shutdown_pc"},
        ],
    }


def can_run(*, user_text, confirm=False):
    t = (user_text or "").lower()
    if "monday morning" in t and ("protocol" in t or "run" in t or "execute" in t):
        return True
    if "shutdown" in t and ("monday morning" in t):
        return True
    return False


def run(*, confirm=False):
    return {"ok": True, "action": "shutdown_pc"}


def should_auto_run_today():
    return datetime.date.today().weekday() == 0
