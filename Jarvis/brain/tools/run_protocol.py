from Jarvis.protocols import run_protocol as _run_protocol
from Jarvis.protocols import get_protocol as _get_protocol
from Jarvis.protocols.farewells import pick as _pick_farewell
from Jarvis.protocols.reactions import pick as _pick_reaction

import os


def _log_error(context, error):
    print(f"{context}: {error}")


def spec():
    return {
        "name": "run_protocol",
        "description": "Execute a named protocol (may have side effects).",
        "args": {"name": "string", "args": "object", "confirm": "boolean", "dry_run": "boolean"},
        "side_effects": True,
        "required": ["name"],
    }


def can_run(*, user_text, name="", args=None, confirm=False, dry_run=False):
    t = (user_text or "").lower()
    name = (name or "").lower()
    return (
        (name and name in t)
        or ("run protocol" in t)
        or ("execute protocol" in t)
        or ("launch protocol" in t)
        or ("start protocol" in t)
        or ("initiate protocol" in t)
        or ("activate protocol" in t)
        or ("trigger protocol" in t)
        or ("fire protocol" in t)
    )


def run(*, assistant=None, wolfram_fn=None, name="", args=None, user_text="", confirm=False, dry_run=False):
    args = args or {}
    if not isinstance(args, dict):
        return {"ok": False, "error_code": "invalid_args"}
    t = (user_text or "").lower()
    explicit = (
        ("run protocol" in t)
        or ("execute protocol" in t)
        or ("launch protocol" in t)
        or ("start protocol" in t)
        or ("initiate protocol" in t)
        or ("activate protocol" in t)
        or ("trigger protocol" in t)
        or ("fire protocol" in t)
    )
    effective_confirm = bool(confirm) or explicit
    proto_module = _get_protocol(name)
    proto_name = ""
    proto_spec = {}
    if proto_module is not None:
        try:
            proto_spec = proto_module.spec() or {}
            proto_name = proto_spec.get("name", "") or ""
        except Exception:
            proto_name = (name or "").strip().lower()
    else:
        proto_name = (name or "").strip().lower()

    if assistant is not None and not bool(dry_run):
        try:
            assistant.tts(_pick_reaction(proto_name, user_text=user_text, spec=proto_spec))
        except Exception as e:
            _log_error("Protocol reaction speech failed", e)

    result = _run_protocol(
        name=name,
        user_text=user_text,
        confirm=effective_confirm,
        dry_run=bool(dry_run),
        args=args,
        assistant=assistant,
        wolfram_fn=wolfram_fn,
    )
    if not isinstance(result, dict):
        return {"ok": True, "data": result}

    if not result.get("ok"):
        return result

    action = (result.get("action") or "").strip().lower()
    proto = (name or "").strip().lower()

    farewell = None
    if action in ("shutdown_app", "shutdown_pc") or proto in ("monday", "monday_morning", "monday morning"):
        farewell = _pick_farewell(proto or "monday")

        if assistant is not None:
            # Clean GUI shutdown if available (may be called from worker thread).
            requested = getattr(assistant, "request_app_shutdown", None)
            if action == "shutdown_pc" or proto.replace(" ", "_") == "monday_morning":
                # Speak immediately before the system shutdown starts.
                try:
                    assistant.tts(farewell)
                except Exception as e:
                    _log_error("Farewell speech failed", e)
                if callable(requested):
                    requested("")
            else:
                if callable(requested):
                    requested(farewell)
                else:
                    try:
                        assistant.tts(farewell)
                    except Exception as e:
                        _log_error("Farewell speech failed", e)
        else:
            # Best-effort fallback when no assistant is provided.
            try:
                print(farewell)
            except Exception as e:
                _log_error("Farewell print failed", e)

        if action == "shutdown_pc" or proto == "monday_morning":
            os.system("shutdown /s /t 0")

    if farewell:
        result.setdefault("farewell", farewell)
    return result
