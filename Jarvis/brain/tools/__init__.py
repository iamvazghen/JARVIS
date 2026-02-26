import json
import inspect
from Jarvis.security import validate_source_access
from Jarvis.config import config

from . import clipboard_clear_history
from . import clipboard_get
from . import clipboard_history
from . import clipboard_save
from . import clipboard_set
from . import llm_clipboard_summarize
from . import file_search
from . import meeting_note_create
from . import standup_draft
from . import focus_mode
from . import app_launch_fuzzy
from . import screenshot_ocr
from . import translate_text
from . import explain_error
from . import contacts_manage
from . import todo_manage
from . import git_summary
from . import clean_downloads
from . import batch_rename
from . import ffmpeg_convert
from . import system_health
from . import web_search
from . import env_check
from . import mcp_list_tools
from . import mcp_execute
from . import imgflip_meme
from . import joke
from . import get_date
from . import get_time
from . import google_search
from . import hide_files
from . import ip_address
from . import launch_app
from . import list_protocols
from . import location
from . import my_location
from . import news
from . import open_website
from . import run_protocol
from . import system_info
from . import show_files
from . import switch_window
from . import take_note
from . import take_screenshot
from . import weather
from . import wikipedia
from . import wolframalpha


_TOOL_MODULES = [
    clipboard_get,
    clipboard_set,
    clipboard_save,
    clipboard_history,
    clipboard_clear_history,
    llm_clipboard_summarize,
    file_search,
    meeting_note_create,
    standup_draft,
    focus_mode,
    app_launch_fuzzy,
    screenshot_ocr,
    translate_text,
    explain_error,
    contacts_manage,
    todo_manage,
    git_summary,
    clean_downloads,
    batch_rename,
    ffmpeg_convert,
    system_health,
    web_search,
    env_check,
    mcp_list_tools,
    mcp_execute,
    imgflip_meme,
    joke,
    get_time,
    get_date,
    system_info,
    weather,
    wikipedia,
    news,
    wolframalpha,
    list_protocols,
    run_protocol,
    open_website,
    launch_app,
    google_search,
    take_note,
    location,
    my_location,
    ip_address,
    take_screenshot,
    switch_window,
    hide_files,
    show_files,
]


_REQUIRED_ARG_OVERRIDES = {
    "wolframalpha": ["query"],
    "wikipedia": ["topic"],
    "weather": ["city"],
    "google_search": ["query"],
    "web_search": ["query"],
    "launch_app": ["app"],
    "open_website": ["domain"],
    "location": ["place"],
    "take_note": ["text"],
    "translate_text": ["text", "target_language"],
    "explain_error": ["error_text"],
    "meeting_note_create": ["title"],
    "run_protocol": ["name"],
    "joke": [],
    "mcp_execute": ["tool_name"],
    "imgflip_meme": [],
}


def _get_run_signature(module):
    try:
        return inspect.signature(module.run)
    except Exception:
        return None


def _spec_required_args(module, raw_spec):
    explicit = raw_spec.get("required")
    if isinstance(explicit, list):
        return [str(x) for x in explicit if str(x).strip()]

    name = raw_spec.get("name", "")
    if name in _REQUIRED_ARG_OVERRIDES:
        return list(_REQUIRED_ARG_OVERRIDES[name])

    sig = _get_run_signature(module)
    if sig is None:
        return []

    required = []
    for pname, param in sig.parameters.items():
        if pname in ("assistant", "wolfram_fn", "user_text"):
            continue
        if param.default is inspect._empty:
            required.append(pname)
    return required


def _enrich_spec(module):
    raw = module.spec() or {}
    spec = dict(raw)
    spec.setdefault("args", {})
    spec.setdefault("description", "")
    spec["required"] = _spec_required_args(module, spec)
    return spec


TOOL_SPECS = [_enrich_spec(m) for m in _TOOL_MODULES]

CRITICAL_TOOLS = {
    "run_protocol",
    "hide_files",
    "take_screenshot",
    "launch_app",
    "open_website",
    "mcp_execute",
}


def tools_for_prompt():
    return json.dumps(TOOL_SPECS, indent=2)

def tools_for_prompt_compact():
    compact = []
    for t in TOOL_SPECS:
        compact.append(
            {
                "name": t.get("name"),
                "description": t.get("description", ""),
                "args": t.get("args") or {},
                "required": t.get("required") or [],
                "side_effects": bool(t.get("side_effects")),
            }
        )
    return json.dumps(compact, ensure_ascii=False)


def get_tool_spec(tool_name):
    for spec in TOOL_SPECS:
        if spec.get("name") == tool_name:
            return spec
    return None


def run_tool(*, tool_name, tool_args, user_text, assistant, wolfram_fn, source_context=None):
    tool_args = tool_args or {}

    for m in _TOOL_MODULES:
        module_spec = get_tool_spec(tool_name) or {}
        if m.spec().get("name") == tool_name:
            ctx = source_context if isinstance(source_context, dict) else {}
            sandbox_mode = str(getattr(config, "runtime_sandbox_mode", "0")).lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            owner_only = str(getattr(config, "runtime_owner_only_critical", "1")).lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            role = str(ctx.get("role", "owner")).strip().lower()
            if owner_only and tool_name in CRITICAL_TOOLS and role != "owner":
                return {
                    "ok": False,
                    "tool_name": tool_name,
                    "error_code": "owner_role_required",
                }
            sanitized_args, missing_required = _sanitize_tool_args(module_spec, tool_args)
            if missing_required:
                return {
                    "ok": False,
                    "tool_name": tool_name,
                    "error_code": "missing_required_args",
                    "missing_args": missing_required,
                }
            can_run = getattr(m, "can_run", None)
            if can_run and module_spec.get("side_effects"):
                if not can_run(user_text=user_text, **sanitized_args):
                    return {
                        "ok": False,
                        "tool_name": tool_name,
                        "error_code": "explicit_request_required",
                    }
            if module_spec.get("side_effects"):
                allowed, reason = validate_source_access(source_context or {})
                if not allowed:
                    return {
                        "ok": False,
                        "tool_name": tool_name,
                        "error_code": "source_access_denied",
                        "details": reason,
                    }
            if sandbox_mode and module_spec.get("side_effects"):
                return {
                    "ok": True,
                    "tool_name": tool_name,
                    "sandbox": True,
                    "data": {"dry_run": True, "tool_args": sanitized_args},
                }
            if tool_name == "run_protocol":
                sanitized_args = dict(sanitized_args)
                sanitized_args["user_text"] = user_text
            try:
                raw = m.run(
                    assistant=assistant,
                    wolfram_fn=wolfram_fn,
                    **sanitized_args,
                )
            except Exception as e:
                return {
                    "ok": False,
                    "tool_name": tool_name,
                    "error_code": "tool_exception",
                    "details": str(e),
                }

            if isinstance(raw, dict):
                if "ok" in raw:
                    raw.setdefault("tool_name", tool_name)
                    return raw
                return {"ok": True, "tool_name": tool_name, "data": raw}

            if isinstance(raw, (list, tuple)):
                return {"ok": True, "tool_name": tool_name, "data": list(raw)}

            if isinstance(raw, bool):
                return {"ok": raw, "tool_name": tool_name}

            return {"ok": True, "tool_name": tool_name, "data": raw}

    raise ValueError("Unknown tool: " + str(tool_name))


def _coerce_value(value, expected_type):
    t = str(expected_type or "").strip().lower()
    if not t:
        return value

    if t in ("string", "str"):
        return str(value)

    if t in ("boolean", "bool"):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        s = str(value).strip().lower()
        if s in ("1", "true", "yes", "y", "on"):
            return True
        if s in ("0", "false", "no", "n", "off"):
            return False
        return value

    if t in ("number", "int", "integer", "float"):
        if isinstance(value, (int, float)):
            return value
        s = str(value).strip()
        try:
            if "." in s:
                return float(s)
            return int(s)
        except Exception:
            return value

    if t in ("object", "dict", "map"):
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            s = value.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    return value
        return value

    if t in ("list", "array"):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            s = value.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    return value
        return value

    return value


def _sanitize_tool_args(spec, tool_args):
    args_spec = (spec or {}).get("args") or {}
    required = list((spec or {}).get("required") or [])
    incoming = tool_args or {}
    clean = {}
    for k, expected_type in args_spec.items():
        if k not in incoming:
            continue
        clean[k] = _coerce_value(incoming.get(k), expected_type)

    missing = []
    for k in required:
        if k not in clean:
            missing.append(k)
            continue
        v = clean.get(k)
        if v is None:
            missing.append(k)
            continue
        if isinstance(v, str) and not v.strip():
            missing.append(k)
    return clean, missing
