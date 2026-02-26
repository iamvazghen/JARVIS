import datetime
from pathlib import Path
import os
import subprocess


def spec():
    return {
        "name": "meeting_note_create",
        "description": "Create a meeting note markdown file from a template and open it (side effect).",
        "args": {"title": "string", "attendees": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, title="", attendees=""):
    t = (user_text or "").lower()
    return ("meeting note" in t) or ("create note" in t) or ("meeting minutes" in t)


def run(*, assistant=None, wolfram_fn=None, title="", attendees=""):
    title = (title or "Meeting").strip()
    attendees = (attendees or "").strip()
    now = datetime.datetime.now()
    safe_stamp = now.strftime("%Y-%m-%d_%H-%M")
    notes_dir = Path.cwd() / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    path = notes_dir / f"{safe_stamp}-{title.replace(' ', '_')}.md"

    content = "\n".join(
        [
            f"# {title}",
            f"- Date: {now.strftime('%Y-%m-%d')}",
            f"- Time: {now.strftime('%H:%M')}",
            f"- Attendees: {attendees}" if attendees else "- Attendees: ",
            "",
            "## Agenda",
            "- ",
            "",
            "## Notes",
            "- ",
            "",
            "## Decisions",
            "- ",
            "",
            "## Action Items",
            "- [ ] ",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")

    editor = "notepad.exe"
    notepadpp = "C://Program Files (x86)//Notepad++//notepad++.exe"
    if os.path.exists(notepadpp):
        editor = notepadpp
    subprocess.Popen([editor, str(path)])
    return str(path)

