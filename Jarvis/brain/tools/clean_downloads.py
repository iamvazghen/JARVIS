from pathlib import Path
import shutil


def _log_error(context, error):
    print(f"{context}: {error}")


def spec():
    return {
        "name": "clean_downloads",
        "description": "Organize files in your Downloads folder into subfolders by type (side effect). Requires confirm.",
        "args": {"confirm": "boolean"},
        "side_effects": True,
    }


def can_run(*, user_text, confirm=False):
    t = (user_text or "").lower()
    return ("clean downloads" in t) or ("organize downloads" in t) or bool(confirm)


def run(*, assistant=None, wolfram_fn=None, confirm=False):
    if not confirm:
        return {"ok": False, "error_code": "confirmation_required"}

    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        return {"ok": False, "error_code": "downloads_not_found"}

    buckets = {
        "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp"},
        "Docs": {".pdf", ".docx", ".doc", ".txt", ".md"},
        "Archives": {".zip", ".rar", ".7z"},
        "Installers": {".exe", ".msi"},
        "Audio": {".mp3", ".wav", ".m4a"},
        "Video": {".mp4", ".mkv", ".mov"},
    }

    moved = []
    errors = []
    for p in downloads.iterdir():
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        dest_dir = None
        for name, exts in buckets.items():
            if ext in exts:
                dest_dir = downloads / name
                break
        if not dest_dir:
            continue
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / p.name
        try:
            shutil.move(str(p), str(dest))
            moved.append(str(dest))
        except (OSError, shutil.Error) as e:
            errors.append({"file": str(p), "error": str(e)})
            _log_error("Failed to move file", e)

    return {
        "ok": True,
        "moved": moved[:100],
        "moved_count": len(moved),
        "errors": errors[:25],
        "error_count": len(errors),
    }
