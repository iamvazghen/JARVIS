import subprocess


def spec():
    return {
        "name": "git_summary",
        "description": "Summarize git status or diff for the current repo.",
        "args": {"what": "string"},
    }


def run(*, assistant=None, wolfram_fn=None, what="status"):
    what = (what or "status").strip().lower()
    try:
        if what == "status":
            out = subprocess.check_output(["git", "status", "--porcelain"], text=True, stderr=subprocess.STDOUT)
            lines = [l for l in out.splitlines() if l.strip()]
            return {"changed_files": len(lines), "lines": lines[:50]}
        if what == "diff":
            out = subprocess.check_output(["git", "diff", "--stat"], text=True, stderr=subprocess.STDOUT)
            return out.strip()
        return {"ok": False, "error": "what must be status or diff"}
    except Exception:
        return {"ok": False, "error": "git command failed"}

