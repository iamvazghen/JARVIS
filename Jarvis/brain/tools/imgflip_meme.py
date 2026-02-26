import random
import os

import requests


def spec():
    return {
        "name": "imgflip_meme",
        "description": "Imgflip API tool: get/search templates, generate image/gif memes, and AI meme endpoints.",
        "args": {
            "action": "string",
            "top_text": "string",
            "bottom_text": "string",
            "template_id": "string",
            "query": "string",
            "meme_type": "string",
            "boxes": "array",
            "model": "string",
            "prefix_text": "string",
            "include_nsfw": "boolean",
            "no_watermark": "boolean",
            "payload": "object",
        },
    }


def _pick_template_id():
    try:
        resp = requests.get("https://api.imgflip.com/get_memes", timeout=10)
        data = resp.json() if resp.ok else {}
    except Exception:
        return "181913649"  # Drake Hotline Bling
    memes = (((data or {}).get("data") or {}).get("memes")) or []
    if not memes:
        return "181913649"
    choices = [m.get("id") for m in memes if isinstance(m, dict) and m.get("id")]
    if not choices:
        return "181913649"
    return random.choice(choices)


def _credentials():
    username = (os.getenv("JIVAN_IMGFLIP_USERNAME", "") or "").strip()
    password = (os.getenv("JIVAN_IMGFLIP_PASSWORD", "") or "").strip()
    return username, password


def _require_credentials():
    username, password = _credentials()
    if not username or not password:
        return None, {
            "ok": False,
            "error_code": "missing_credentials",
            "details": "Set JIVAN_IMGFLIP_USERNAME and JIVAN_IMGFLIP_PASSWORD.",
        }
    return (username, password), None


def _flatten_boxes(boxes):
    rows = []
    if not isinstance(boxes, list):
        return rows
    for i, box in enumerate(boxes):
        if not isinstance(box, dict):
            continue
        for k, v in box.items():
            rows.append((f"boxes[{i}][{k}]", str(v)))
    return rows


def _post(endpoint, form):
    try:
        resp = requests.post(f"https://api.imgflip.com/{endpoint}", data=form, timeout=20)
        data = resp.json() if resp.ok else {}
    except Exception as e:
        return {"ok": False, "error_code": "request_failed", "details": str(e)}
    if not isinstance(data, dict) or not data.get("success"):
        return {
            "ok": False,
            "error_code": "imgflip_failed",
            "details": (data or {}).get("error_message", "Unknown Imgflip error."),
            "data": data,
        }
    return {"ok": True, "data": data.get("data") or {}}


def _build_caption_form(*, template_id, top_text, bottom_text, boxes, no_watermark):
    creds, err = _require_credentials()
    if err:
        return None, err
    username, password = creds
    form = [
        ("template_id", str(template_id).strip() or _pick_template_id()),
        ("username", username),
        ("password", password),
    ]
    if boxes:
        form.extend(_flatten_boxes(boxes))
    else:
        form.append(("text0", top_text))
        form.append(("text1", bottom_text))
    if no_watermark:
        form.append(("no_watermark", "1"))
    return form, None


def run(
    *,
    assistant=None,
    wolfram_fn=None,
    action="caption_image",
    top_text="",
    bottom_text="",
    template_id="",
    query="",
    meme_type="",
    boxes=None,
    model="",
    prefix_text="",
    include_nsfw=False,
    no_watermark=False,
    payload=None,
):
    action_name = str(action or "caption_image").strip().lower()
    top = (top_text or "").strip()
    bottom = (bottom_text or "").strip()
    q = (query or "").strip()
    t = (meme_type or "").strip()
    incoming = payload if isinstance(payload, dict) else {}

    if action_name == "get_memes":
        params = {}
        if t:
            params["type"] = t
        try:
            resp = requests.get("https://api.imgflip.com/get_memes", params=params, timeout=20)
            data = resp.json() if resp.ok else {}
        except Exception as e:
            return {"ok": False, "error_code": "request_failed", "details": str(e)}
        if not isinstance(data, dict) or not data.get("success"):
            return {
                "ok": False,
                "error_code": "imgflip_failed",
                "details": (data or {}).get("error_message", "Unknown Imgflip error."),
                "data": data,
            }
        return {"ok": True, "action": action_name, "data": data.get("data") or {}}

    if action_name == "caption_image":
        if not top and not bottom and not boxes:
            return {"ok": False, "error_code": "missing_text", "details": "Provide text or boxes."}
        form, err = _build_caption_form(
            template_id=template_id, top_text=top, bottom_text=bottom, boxes=boxes, no_watermark=no_watermark
        )
        if err:
            return err
        res = _post("caption_image", form)
        if not res.get("ok"):
            return res
        result = res.get("data") or {}
        return {"ok": True, "action": action_name, "url": result.get("url", ""), "page_url": result.get("page_url", "")}

    if action_name == "caption_gif":
        if not boxes:
            return {"ok": False, "error_code": "missing_boxes", "details": "caption_gif requires boxes."}
        form, err = _build_caption_form(
            template_id=template_id, top_text="", bottom_text="", boxes=boxes, no_watermark=no_watermark
        )
        if err:
            return err
        res = _post("caption_gif", form)
        if not res.get("ok"):
            return res
        result = res.get("data") or {}
        return {"ok": True, "action": action_name, "url": result.get("url", ""), "page_url": result.get("page_url", "")}

    creds, err = _require_credentials()
    if err:
        return err
    username, password = creds

    if action_name == "search_memes":
        form = [("username", username), ("password", password), ("query", q)]
        if t:
            form.append(("type", t))
        if include_nsfw:
            form.append(("include_nsfw", "1"))
        return _post("search_memes", form)

    if action_name == "get_meme":
        tid = (template_id or "").strip() or str(incoming.get("template_id", "")).strip()
        if not tid:
            return {"ok": False, "error_code": "missing_template_id"}
        return _post("get_meme", [("username", username), ("password", password), ("template_id", tid)])

    if action_name == "automeme":
        text = top or q or str(incoming.get("text", "")).strip()
        if not text:
            return {"ok": False, "error_code": "missing_text"}
        form = [("username", username), ("password", password), ("text", text)]
        if no_watermark:
            form.append(("no_watermark", "1"))
        return _post("automeme", form)

    if action_name == "ai_meme":
        form = [("username", username), ("password", password)]
        m = (model or "").strip() or str(incoming.get("model", "")).strip()
        if m:
            form.append(("model", m))
        tid = (template_id or "").strip() or str(incoming.get("template_id", "")).strip()
        if tid:
            form.append(("template_id", tid))
        pref = (prefix_text or "").strip() or str(incoming.get("prefix_text", "")).strip()
        if pref:
            form.append(("prefix_text", pref))
        if no_watermark:
            form.append(("no_watermark", "1"))
        return _post("ai_meme", form)

    return {"ok": False, "error_code": "unsupported_action", "details": action_name}
