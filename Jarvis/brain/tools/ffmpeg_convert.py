import shutil
import subprocess
from pathlib import Path


def spec():
    return {
        "name": "ffmpeg_convert",
        "description": "Convert media files using ffmpeg (side effect). Requires ffmpeg installed and confirm.",
        "args": {"input_path": "string", "output_path": "string", "confirm": "boolean"},
        "side_effects": True,
    }


def can_run(*, user_text, confirm=False, input_path="", output_path=""):
    t = (user_text or "").lower()
    return ("convert" in t) or ("ffmpeg" in t) or bool(confirm)


def run(*, assistant=None, wolfram_fn=None, input_path="", output_path="", confirm=False):
    if not confirm:
        return {"ok": False, "error_code": "confirmation_required"}

    if not shutil.which("ffmpeg"):
        return {"ok": False, "error_code": "ffmpeg_not_found"}

    inp = Path(input_path or "")
    out = Path(output_path or "")
    if not inp.exists():
        return {"ok": False, "error_code": "input_not_found"}
    if not out:
        return {"ok": False, "error_code": "missing_output_path"}

    try:
        subprocess.check_output(["ffmpeg", "-y", "-i", str(inp), str(out)], stderr=subprocess.STDOUT, text=True)
        return {"ok": True, "output": str(out)}
    except Exception:
        return {"ok": False, "error_code": "ffmpeg_failed"}
