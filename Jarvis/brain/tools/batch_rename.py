from pathlib import Path


def _log_error(context, error):
    print(f"{context}: {error}")


def spec():
    return {
        "name": "batch_rename",
        "description": "Batch rename files in a folder using a simple prefix/suffix pattern (side effect). Requires confirm.",
        "args": {"directory": "string", "prefix": "string", "suffix": "string", "confirm": "boolean"},
        "side_effects": True,
    }


def can_run(*, user_text, confirm=False, directory="", prefix="", suffix=""):
    t = (user_text or "").lower()
    return ("rename" in t) or ("batch rename" in t) or bool(confirm)


def run(*, assistant=None, wolfram_fn=None, directory=".", prefix="", suffix="", confirm=False):
    if not confirm:
        return {"ok": False, "error_code": "confirmation_required"}

    d = Path(directory or ".")
    if not d.exists():
        return {"ok": False, "error_code": "directory_not_found"}

    changed = []
    errors = []
    for p in d.iterdir():
        if not p.is_file():
            continue
        new_name = f"{prefix}{p.stem}{suffix}{p.suffix}"
        new_path = p.with_name(new_name)
        if new_path == p:
            continue
        try:
            p.rename(new_path)
            changed.append({"from": str(p), "to": str(new_path)})
        except OSError as e:
            errors.append({"from": str(p), "to": str(new_path), "error": str(e)})
            _log_error("Failed to rename file", e)
    return {
        "ok": True,
        "changed": changed[:100],
        "changed_count": len(changed),
        "errors": errors[:25],
        "error_count": len(errors),
    }
