import datetime
import hashlib
import json
import os
import re
import uuid


def _now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _normalize_phrase(text):
    return re.sub(r"\s+", " ", str(text or "").strip().lower().replace("_", " "))


def _log_path():
    return os.path.join(os.path.dirname(__file__), "protocol_runs.log")


class ProtocolEngine:
    def __init__(self):
        self._last_runs = {}
        self._seen_idempotency = set()

    def normalize_spec(self, spec):
        s = dict(spec or {})
        s.setdefault("name", "")
        s.setdefault("aliases", [])
        s.setdefault("description", "")
        s.setdefault("side_effects", False)
        s.setdefault("requires_confirmation", False)
        s.setdefault("confirmation_policy", "if_side_effects")
        s.setdefault("triggers", [])
        s.setdefault("negative_triggers", [])
        s.setdefault("args_schema", {})
        s.setdefault("cooldown_s", 0)
        s.setdefault("steps", [])
        return s

    def list_specs(self, modules):
        return [self.normalize_spec(m.spec()) for m in modules]

    def get_protocol(self, modules, name):
        target = (name or "").strip().lower()
        if not target:
            return None
        for m in modules:
            spec = self.normalize_spec(m.spec())
            if spec.get("name", "").strip().lower() == target:
                return m
            aliases = [str(a).strip().lower() for a in (spec.get("aliases") or [])]
            if target in aliases:
                return m
        return None

    def resolve_protocol(self, modules, *, name="", user_text=""):
        if name:
            return self.get_protocol(modules, name)
        text = (user_text or "").strip().lower()
        if not text:
            return None
        norm_text = _normalize_phrase(text)

        # Generic command pattern support so users can say:
        # "run/execute/start/initiate/activate/trigger protocol <name>"
        verb_patterns = (
            "run protocol ",
            "execute protocol ",
            "launch protocol ",
            "start protocol ",
            "initiate protocol ",
            "activate protocol ",
            "trigger protocol ",
            "fire protocol ",
        )
        for prefix in verb_patterns:
            if norm_text.startswith(prefix):
                requested = norm_text[len(prefix) :].strip()
                if requested:
                    direct = self.get_protocol(modules, requested)
                    if direct:
                        return direct

        best = None
        best_score = 0
        for m in modules:
            spec = self.normalize_spec(m.spec())
            triggers = [str(t).strip().lower() for t in (spec.get("triggers") or []) if str(t).strip()]
            negatives = [str(t).strip().lower() for t in (spec.get("negative_triggers") or []) if str(t).strip()]
            if any(n in text for n in negatives):
                continue
            score = 0
            name_tokens = [_normalize_phrase(spec.get("name", ""))]
            name_tokens.extend([_normalize_phrase(a) for a in (spec.get("aliases") or [])])
            for token in name_tokens:
                if token and token in norm_text:
                    score = max(score, len(token))
            for trig in triggers:
                trig_norm = _normalize_phrase(trig)
                if trig_norm and trig_norm in norm_text:
                    # Longer matches are usually more specific.
                    score = max(score, len(trig_norm))
            if score > best_score:
                best = m
                best_score = score
        return best

    def run(
        self,
        modules,
        *,
        name="",
        user_text="",
        confirm=False,
        dry_run=False,
        args=None,
        idempotency_key="",
        assistant=None,
        wolfram_fn=None,
    ):
        protocol = self.resolve_protocol(modules, name=name, user_text=user_text)
        if not protocol:
            return {"ok": False, "error_code": "unknown_protocol", "error": "Unknown protocol."}

        spec = self.normalize_spec(protocol.spec())
        pname = spec.get("name", "")
        run_id = str(uuid.uuid4())
        args = dict(args or {})

        if not self._check_confirmation(spec, user_text=user_text, confirm=confirm):
            return {
                "ok": False,
                "protocol": pname,
                "run_id": run_id,
                "error_code": "confirmation_required",
                "requires_confirmation": True,
            }

        missing = self._missing_required_args(spec, args)
        if missing:
            return {
                "ok": False,
                "protocol": pname,
                "run_id": run_id,
                "error_code": "missing_required_args",
                "missing_args": missing,
            }

        cooldown_s = int(spec.get("cooldown_s") or 0)
        now_ts = datetime.datetime.now().timestamp()
        last_ts = self._last_runs.get(pname)
        if cooldown_s > 0 and last_ts and (now_ts - last_ts) < cooldown_s:
            return {
                "ok": False,
                "protocol": pname,
                "run_id": run_id,
                "error_code": "cooldown_active",
                "retry_after_s": max(1, int(cooldown_s - (now_ts - last_ts))),
            }

        key = (idempotency_key or "").strip()
        if not key:
            key = self._default_idempotency_key(pname, args)
        if key in self._seen_idempotency:
            return {
                "ok": False,
                "protocol": pname,
                "run_id": run_id,
                "error_code": "duplicate_idempotency_key",
            }

        if dry_run:
            steps = self._build_steps(protocol, spec, args=args, user_text=user_text)
            result = {
                "ok": True,
                "protocol": pname,
                "run_id": run_id,
                "dry_run": True,
                "steps": steps,
            }
            self._log_run(result)
            return result

        steps = self._build_steps(protocol, spec, args=args, user_text=user_text)
        exec_result = self._execute_steps(
            modules,
            steps=steps,
            user_text=user_text,
            confirm=confirm,
            dry_run=dry_run,
            assistant=assistant,
            wolfram_fn=wolfram_fn,
        )
        exec_result.setdefault("protocol", pname)
        exec_result.setdefault("run_id", run_id)
        exec_result.setdefault("steps", steps)
        exec_result.setdefault("idempotency_key", key)
        self._seen_idempotency.add(key)
        self._last_runs[pname] = now_ts
        self._log_run(exec_result)
        return exec_result

    def _build_steps(self, protocol, spec, *, args, user_text):
        builder = getattr(protocol, "build_steps", None)
        if callable(builder):
            built = builder(args=args, user_text=user_text)
            if isinstance(built, list):
                return built
        return list(spec.get("steps") or [])

    def _execute_steps(self, modules, *, steps, user_text, confirm, dry_run, assistant, wolfram_fn):
        events = []
        final_action = None
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                return {"ok": False, "error_code": "invalid_step", "step_index": idx}
            stype = (step.get("type") or "").strip().lower()
            if stype == "say":
                text = str(step.get("text") or "").strip()
                events.append({"type": "say", "text": text})
                continue
            if stype == "action":
                name = (step.get("name") or "").strip().lower()
                events.append({"type": "action", "name": name})
                if name in ("shutdown_app", "shutdown_pc"):
                    final_action = name
                continue
            if stype == "protocol":
                nested = str(step.get("name") or "").strip()
                nested_args = step.get("args") or {}
                nested_result = self.run(
                    modules,
                    name=nested,
                    user_text=user_text,
                    confirm=confirm,
                    dry_run=dry_run,
                    args=nested_args,
                    assistant=assistant,
                    wolfram_fn=wolfram_fn,
                )
                events.append({"type": "protocol", "name": nested, "result": nested_result})
                if not nested_result.get("ok"):
                    return {
                        "ok": False,
                        "error_code": "nested_protocol_failed",
                        "step_index": idx,
                        "nested": nested_result,
                        "events": events,
                    }
                if nested_result.get("action") in ("shutdown_app", "shutdown_pc"):
                    final_action = nested_result.get("action")
                continue
            if stype == "tool":
                tool_name = str(step.get("name") or "").strip()
                tool_args = step.get("args") or {}
                if not tool_name:
                    return {"ok": False, "error_code": "invalid_tool_step", "step_index": idx, "events": events}
                if not isinstance(tool_args, dict):
                    return {"ok": False, "error_code": "invalid_tool_args", "step_index": idx, "events": events}
                try:
                    # Lazy import avoids module cycles at import time.
                    from Jarvis.brain.tools import run_tool  # type: ignore
                except Exception as e:
                    return {
                        "ok": False,
                        "error_code": "tool_runner_unavailable",
                        "step_index": idx,
                        "details": str(e),
                        "events": events,
                    }
                tool_result = run_tool(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    user_text=user_text,
                    assistant=assistant,
                    wolfram_fn=wolfram_fn,
                )
                events.append({"type": "tool", "name": tool_name, "result": tool_result})
                if not isinstance(tool_result, dict) or not tool_result.get("ok"):
                    return {
                        "ok": False,
                        "error_code": "tool_step_failed",
                        "step_index": idx,
                        "tool_result": tool_result,
                        "events": events,
                    }
                if tool_result.get("action") in ("shutdown_app", "shutdown_pc"):
                    final_action = tool_result.get("action")
                continue

            return {"ok": False, "error_code": "unknown_step_type", "step_index": idx, "events": events}

        result = {"ok": True, "events": events}
        if final_action:
            result["action"] = final_action
        return result

    def _check_confirmation(self, spec, *, user_text, confirm):
        policy = str(spec.get("confirmation_policy") or "if_side_effects").strip().lower()
        if policy == "never":
            return True
        if policy == "always":
            return bool(confirm)
        if policy == "explicit_phrase":
            t = (user_text or "").lower()
            explicit = ("run protocol" in t) or ("execute protocol" in t) or ("confirm" in t)
            return bool(confirm) or explicit

        # default: if_side_effects
        if spec.get("requires_confirmation"):
            return bool(confirm)
        if spec.get("side_effects"):
            return bool(confirm)
        return True

    def _missing_required_args(self, spec, args):
        missing = []
        schema = spec.get("args_schema") or {}
        for key, rule in schema.items():
            if not isinstance(rule, dict):
                continue
            if not rule.get("required"):
                continue
            val = args.get(key)
            if val is None:
                missing.append(key)
                continue
            if isinstance(val, str) and not val.strip():
                missing.append(key)
        return missing

    def _default_idempotency_key(self, protocol_name, args):
        day = datetime.date.today().isoformat()
        payload = json.dumps({"protocol": protocol_name, "day": day, "args": args}, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]

    def _log_run(self, record):
        path = _log_path()
        line = {"ts": _now_iso(), **(record or {})}
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        except OSError:
            pass
