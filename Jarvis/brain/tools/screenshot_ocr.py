from pathlib import Path

import pyautogui


def spec():
    return {
        "name": "screenshot_ocr",
        "description": "Take a screenshot and extract text via Tesseract OCR if available (side effect).",
        "args": {"filename": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, filename=""):
    t = (user_text or "").lower()
    return ("ocr" in t) or ("extract text" in t) or ("screenshot" in t)


def run(*, assistant=None, wolfram_fn=None, filename="ocr.png"):
    filename = (filename or "ocr.png").strip()
    if not filename.lower().endswith(".png"):
        filename += ".png"
    path = Path.cwd() / filename
    img = pyautogui.screenshot()
    img.save(str(path))

    try:
        import pytesseract  # type: ignore
    except Exception:
        return {"ok": False, "saved": str(path), "error_code": "ocr_deps_missing"}

    try:
        text = pytesseract.image_to_string(img)
        return {"ok": True, "saved": str(path), "text": text}
    except Exception:
        return {"ok": False, "saved": str(path), "error_code": "ocr_failed"}
