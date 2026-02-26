import datetime


def spec():
    return {
        "name": "standup_draft",
        "description": "Generate a daily standup update template.",
        "args": {"name": "string"},
    }


def run(*, assistant=None, wolfram_fn=None, name=""):
    today = datetime.date.today().isoformat()
    who = (name or "").strip() or "Me"
    return "\n".join(
        [
            f"Standup ({today}) — {who}",
            "",
            "Yesterday:",
            "- ",
            "",
            "Today:",
            "- ",
            "",
            "Blockers:",
            "- ",
        ]
    )

