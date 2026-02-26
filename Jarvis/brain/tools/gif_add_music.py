import shutil
import subprocess
import tempfile
from pathlib import Path

import requests


def spec():
    return {
        "name": "gif_add_music",
        "description": "Add music to a GIF by converting it to MP4 video with audio (side effect). Requires ffmpeg and confirm.",
        "args": {
            "gif_source": "string",
            "audio_source": "string",
            "output_path": "string",
            "confirm": "boolean",
        },
        "side_effects": True,
    }


def can_run(*, user_text, confirm=False, gif_source="", audio_source="", output_path=""):
    t = (user_text or "").lower()
    return ("gif" in t and "music" in t) or ("sound" in t and "gif" in t) or bool(confirm)


def _fetch_if_url(source, suffix):
    src = str(source or "").strip()
    if src.startswith("http://") or src.startswith("https://"):
        resp = requests.get(src, timeout=25)
        resp.raise_for_status()
        f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        f.write(resp.content)
        f.flush()
        f.close()
        return Path(f.name), True
    return Path(src), False


def run(*, assistant=None, wolfram_fn=None, gif_source="", audio_source="", output_path="", confirm=False):
    if not confirm:
        return {"ok": False, "error_code": "confirmation_required"}
    if not shutil.which("ffmpeg"):
        return {"ok": False, "error_code": "ffmpeg_not_found"}
    if not str(gif_source or "").strip() or not str(audio_source or "").strip():
        return {"ok": False, "error_code": "missing_inputs"}
    if not str(output_path or "").strip():
        return {"ok": False, "error_code": "missing_output_path"}

    temp_paths = []
    try:
        gif_path, gif_temp = _fetch_if_url(gif_source, ".gif")
        audio_path, audio_temp = _fetch_if_url(audio_source, ".audio")
        if gif_temp:
            temp_paths.append(gif_path)
        if audio_temp:
            temp_paths.append(audio_path)

        if not gif_path.exists():
            return {"ok": False, "error_code": "gif_input_not_found"}
        if not audio_path.exists():
            return {"ok": False, "error_code": "audio_input_not_found"}

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(gif_path),
            "-i",
            str(audio_path),
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(out),
        ]
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return {"ok": True, "output": str(out)}
    except Exception as e:
        return {"ok": False, "error_code": "ffmpeg_failed", "details": str(e)}
    finally:
        for p in temp_paths:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
