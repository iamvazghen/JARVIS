import json
import os
import re
import time
import hashlib

from Jarvis.config import config
from Jarvis.protocols import list_protocols

from .llm import LLMError, chat_completions
from .intent_routing import required_noauth_mcp_plan, required_telegram_mcp_plan
from .cache import RedisConversationBuffer
from .mcp import ComposioMCPClient
from .memory import MemoryManager
from .persona import persona_block
from Jarvis.security import validate_source_access
from .tools import get_tool_spec, run_tool, tools_for_prompt_compact
from Jarvis.runtime.errors import humanize
from Jarvis.runtime.replay import replay_event


def _tokenize(text):
    return [t for t in re.split(r"[^a-zA-Z0-9_]+", str(text or "").lower()) if len(t) > 1]


def _extract_json_object(text):
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


def _as_fallback_reply(text):
    if not text:
        return None
    t = str(text).strip()
    if not t:
        return None
    # Keep it bounded to avoid TTS going wild if the model dumps a lot of text.
    return t[:1200]


def _extract_topic_from_text(user_text):
    text = (user_text or "").strip()
    lowered = text.lower()
    for prefix in ("tell me about ", "who is ", "what is "):
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return ""


def _extract_weather_city(user_text):
    lowered = (user_text or "").strip().lower()
    m = re.search(r"\bweather(?:\s+in)?\s+(.+)$", lowered)
    if not m:
        return ""
    return m.group(1).strip()


def _detect_lang_for_joke(user_text):
    s = user_text or ""
    for ch in s:
        code = ord(ch)
        if 0x0530 <= code <= 0x058F:
            return "hy"
        if 0x0400 <= code <= 0x04FF:
            return "ru"
    return "en"


def _extract_after_keyword(text, keyword):
    src = str(text or "")
    lower_src = src.lower()
    idx = lower_src.find(keyword.lower())
    if idx == -1:
        return ""
    return src[idx + len(keyword) :].strip(" :,-")


def _extract_meme_text(user_text):
    text = (user_text or "").strip()
    lowered = text.lower()
    for prefix in ("meme ", "make meme ", "generate meme "):
        if lowered.startswith(prefix):
            body = text[len(prefix) :].strip()
            if "|" in body:
                top, bottom = body.split("|", 1)
                return top.strip(), bottom.strip()
            return body, ""
    return "", ""


def _detect_user_language(user_text, command_context=None):
    ctx = command_context if isinstance(command_context, dict) else {}
    hinted = str(ctx.get("language", "") or "").strip().lower()
    if hinted.startswith("ru"):
        return "ru"
    if hinted.startswith("de"):
        return "de"
    if hinted.startswith("en"):
        return "en"
    for ch in str(user_text or ""):
        code = ord(ch)
        if 0x0400 <= code <= 0x04FF:
            return "ru"
    text_low = str(user_text or "").lower()
    german_markers = (" und ", " bitte ", " danke", " nicht ", " ich ", " ist ", "wie ")
    if any(m in f" {text_low} " for m in german_markers):
        return "de"
    return "en"


def _language_instruction(lang):
    if lang == "ru":
        return "Output language policy: Always reply in Russian unless the user explicitly asks to switch language."
    if lang == "de":
        return "Output language policy: Always reply in German unless the user explicitly asks to switch language."
    return "Output language policy: Always reply in English unless the user explicitly asks to switch language."


def _telegram_owner_hint():
    ids_raw = str(getattr(config, "security_allowed_telegram_user_ids", "") or "").strip()
    names_raw = str(getattr(config, "security_allowed_telegram_usernames", "") or "").strip()
    first_id = ""
    if ids_raw:
        first_id = ids_raw.split(",")[0].strip()
    first_name = ""
    if names_raw:
        first_name = names_raw.split(",")[0].strip().lstrip("@")
    if first_id or first_name:
        return (
            f"Telegram owner context: default owner chat_id/user_id={first_id or 'unknown'}, "
            f"username={first_name or 'unknown'}."
        )
    return ""


def _latency_trace_enabled():
    return str(getattr(config, "latency_trace", "1")).lower() in ("1", "true", "yes", "on")


def _localized_text(lang, *, en, ru=None, de=None):
    if lang == "ru" and ru:
        return ru
    if lang == "de" and de:
        return de
    return en


def _fast_tool_reply(tool_name, tool_result, user_lang):
    name = str(tool_name or "").strip()
    if not isinstance(tool_result, dict):
        return ""
    ok = bool(tool_result.get("ok"))
    if name == "mcp_execute":
        data = tool_result.get("data") if isinstance(tool_result.get("data"), dict) else {}
        executed_tool = str(data.get("tool_name", ""))
        if executed_tool.startswith("TELEGRAM_SEND_"):
            if ok:
                return _localized_text(
                    user_lang,
                    en="Done. Sent to your Telegram DM.",
                    ru="Готово. Отправил в ваш Telegram DM.",
                    de="Fertig. An Ihre Telegram-DM gesendet.",
                )
            return _localized_text(
                user_lang,
                en="Telegram send failed. Please try again.",
                ru="Не удалось отправить в Telegram. Попробуйте снова.",
                de="Telegram-Senden fehlgeschlagen. Bitte erneut versuchen.",
            )
    if name == "imgflip_meme" and ok:
        url = str(tool_result.get("url", "")).strip()
        if url:
            return _localized_text(
                user_lang,
                en=f"Meme created: {url}",
                ru=f"Мем создан: {url}",
                de=f"Meme erstellt: {url}",
            )
    return ""


def _required_noauth_mcp_plan(user_text):
    return required_noauth_mcp_plan(user_text)


def _required_tool_plan(user_text, recent_messages=None):
    text = (user_text or "").strip()
    lowered = text.lower()
    if not lowered:
        return None

    telegram_plan = required_telegram_mcp_plan(text, recent_messages=recent_messages)
    if telegram_plan:
        return telegram_plan

    mcp_noauth = _required_noauth_mcp_plan(text)
    if mcp_noauth:
        return mcp_noauth

    if "protocol" in lowered or lowered in ("monday", "monday morning"):
        if "monday morning" in lowered:
            return ("run_protocol", {"name": "monday_morning", "confirm": True})
        if "monday" in lowered:
            return ("run_protocol", {"name": "monday", "confirm": True})

    # Explicit deterministic routing to prevent LLM-memory answers where tools exist.
    if "joke" in lowered or "make me laugh" in lowered or "funny" in lowered:
        return ("joke", {"language": _detect_lang_for_joke(text)})

    if lowered.startswith("meme ") or lowered.startswith("make meme ") or lowered.startswith("generate meme "):
        top_text, bottom_text = _extract_meme_text(text)
        return ("imgflip_meme", {"top_text": top_text, "bottom_text": bottom_text})

    if "calculate" in lowered:
        return ("wolframalpha", {"query": text})

    if re.search(r"\d+\s*[\+\-\*/^%]\s*\d+", lowered):
        return ("wolframalpha", {"query": text})

    if lowered.startswith("who is ") or lowered.startswith("tell me about "):
        topic = _extract_topic_from_text(text)
        if topic:
            return ("wikipedia", {"topic": topic})

    if lowered.startswith("what is "):
        topic = _extract_topic_from_text(text)
        if topic:
            # Prefer Wolfram for formula-like questions, otherwise Wikipedia.
            if re.search(r"\d", topic) or any(op in topic for op in ("+", "-", "*", "/", "^", "%")):
                return ("wolframalpha", {"query": text})
            return ("wikipedia", {"topic": topic})

    if "weather" in lowered:
        city = _extract_weather_city(text)
        if city:
            return ("weather", {"city": city})

    if "news" in lowered or "headlines" in lowered:
        return ("news", {})

    if "ip address" in lowered:
        return ("ip_address", {})

    if "time" in lowered and "timer" not in lowered:
        return ("get_time", {})

    if re.search(r"\bdate\b", lowered):
        return ("get_date", {})

    return None


class JarvisBrain:
    def __init__(self, *, assistant, wolfram_fn):
        self._assistant = assistant
        self._wolfram_fn = wolfram_fn
        self._history = []
        self._soul_text = None
        self._soul_mtime = None
        self._soul_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "SOUL.md")
        )
        self._memory = MemoryManager()
        self._mcp = ComposioMCPClient()
        self._redis_buffer = RedisConversationBuffer()
        self._semantic_cache = {}
        self._tool_cache = {}
        self._stats = {"llm_calls": 0, "tool_calls": 0, "cache_hits": 0}
        self._tools_prompt_cache = tools_for_prompt_compact()
        self._protocols_prompt_cache = json.dumps(list_protocols(), indent=2)
        self._base_instructions = (
            "Strict output contract (IMPORTANT):\n"
            "- Respond with EXACTLY ONE JSON object and nothing else.\n"
            '- Reply: {"action":"reply","reply":"..."}\n'
            '- Tool call: {"action":"tool","tool_name":"...","tool_args":{...}}\n'
            "- Use at most ONE tool call per turn.\n"
            "- Never fabricate tool/protocol results.\n"
            "\n"
            "Tool & protocol policy:\n"
            "- Tool-first policy: if any available tool can answer the request, you MUST call a tool and MUST NOT answer from memory.\n"
            "- Use action=reply only for pure small-talk/opinion/chitchat with no matching tool.\n"
            "- Prefer info-only tools when possible.\n"
            "- Side-effect tools (opening apps/websites, sending email, screenshots, hiding files, shutdown) must only be used when the user explicitly asked.\n"
            "- Protocols are named command bundles; use `run_protocol` to execute them.\n"
            "- Telegram default DM target is preconfigured for the owner. For telegram send/reply requests, use Telegram tools directly and do not ask for chat_id unless a tool call explicitly fails for missing chat_id.\n"
            "\n"
            "Routing hints:\n"
            "- If the user says \"open <app>\" (e.g. Excel, Word, Chrome), prefer the `launch_app` tool.\n"
            "- If the user says \"open <domain/url>\" (e.g. github.com), use `open_website`.\n"
            "- If the user says \"search\" / \"look up\", use `web_search` or `google_search`.\n"
        )

    def _settings(self):
        api_key = getattr(config, "llm_api_key", "") or ""
        base_url = getattr(config, "llm_base_url", "") or ""
        model = getattr(config, "llm_model", "") or ""

        return api_key, base_url, model

    def enabled(self):
        api_key, base_url, model = self._settings()
        return bool(api_key and base_url and model)

    def mem0_health(self, force=False):
        return self._memory.health_check(force=force)

    def mcp_health(self, force=False):
        return self._mcp.health_check(force=force)

    def redis_health(self, force=False):
        return self._redis_buffer.health_check(force=force)

    def runtime_stats(self):
        return dict(self._stats)

    def _normalize_query(self, text):
        return " ".join(_tokenize(text))

    def _semantic_cache_get(self, key):
        ttl = int(getattr(config, "brain_semantic_cache_ttl_s", 45))
        row = self._semantic_cache.get(key)
        if not row:
            return None
        if (time.time() - float(row.get("ts", 0))) > max(1, ttl):
            self._semantic_cache.pop(key, None)
            return None
        self._stats["cache_hits"] += 1
        return row.get("reply")

    def _semantic_cache_set(self, key, reply):
        self._semantic_cache[key] = {"ts": time.time(), "reply": str(reply or "")}
        if len(self._semantic_cache) > 200:
            # bounded cache
            oldest = sorted(self._semantic_cache.items(), key=lambda x: x[1].get("ts", 0))[:40]
            for k, _ in oldest:
                self._semantic_cache.pop(k, None)

    def _tool_cache_key(self, tool_name, tool_args):
        raw = json.dumps({"tool": tool_name, "args": tool_args or {}}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _tool_cache_get(self, tool_name, tool_args):
        ttl = int(getattr(config, "brain_tool_cache_ttl_s", 60))
        key = self._tool_cache_key(tool_name, tool_args)
        row = self._tool_cache.get(key)
        if not row:
            return None
        if (time.time() - float(row.get("ts", 0))) > max(1, ttl):
            self._tool_cache.pop(key, None)
            return None
        self._stats["cache_hits"] += 1
        return row.get("result")

    def _tool_cache_set(self, tool_name, tool_args, result):
        key = self._tool_cache_key(tool_name, tool_args)
        self._tool_cache[key] = {"ts": time.time(), "result": result}
        if len(self._tool_cache) > 200:
            oldest = sorted(self._tool_cache.items(), key=lambda x: x[1].get("ts", 0))[:40]
            for k, _ in oldest:
                self._tool_cache.pop(k, None)

    def _cacheable_tool(self, tool_name):
        return str(tool_name or "") in {"weather", "news", "ip_address", "get_time", "get_date", "wikipedia"}

    def _smalltalk_reply(self, text, lang):
        lowered = str(text or "").strip().lower()
        if lowered in ("hi", "hello", "hey", "good morning", "good evening"):
            return _localized_text(
                lang,
                en="Hello. How can I help?",
                ru="Здравствуйте. Чем могу помочь?",
                de="Hallo. Wie kann ich helfen?",
            )
        if lowered in ("thanks", "thank you", "спасибо", "danke"):
            return _localized_text(lang, en="You're welcome.", ru="Пожалуйста.", de="Gern geschehen.")
        return ""

    def _route_model(self, user_text, default_model):
        text = str(user_text or "")
        # route complex reasoning to full model, everything else to fast model
        complex_markers = ("analyze", "compare", "plan", "strategy", "why", "architecture", "security audit")
        if len(text) > 220 or any(m in text.lower() for m in complex_markers):
            return getattr(config, "llm_model", "") or default_model
        return getattr(config, "llm_fast_model", "") or default_model

    def _apply_prompt_budget(self, messages):
        budget = int(getattr(config, "llm_prompt_char_budget", 12000))
        if budget <= 0:
            return messages
        total = 0
        out = []
        for row in reversed(messages):
            txt = str(row.get("content", ""))
            piece = len(txt)
            if total + piece > budget and out:
                continue
            out.append(row)
            total += piece
            if total >= budget:
                break
        return list(reversed(out))

    def _deterministic_fill_tool_args(self, *, tool_name, user_text, tool_args):
        args = dict(tool_args or {})
        name = str(tool_name or "")
        text = str(user_text or "")
        if name == "weather" and not args.get("city"):
            city = _extract_weather_city(text)
            if city:
                args["city"] = city
        if name == "wikipedia" and not args.get("topic"):
            topic = _extract_topic_from_text(text)
            if topic:
                args["topic"] = topic
        if name == "wolframalpha" and not args.get("query"):
            args["query"] = text
        if name == "mcp_execute" and not args.get("tool_name"):
            plan = _required_tool_plan(text, recent_messages=self._merged_history())
            if plan and plan[0] == "mcp_execute":
                p_args = plan[1] if isinstance(plan[1], dict) else {}
                if p_args.get("tool_name"):
                    args["tool_name"] = p_args.get("tool_name")
                    if not args.get("tool_input") and isinstance(p_args.get("tool_input"), dict):
                        args["tool_input"] = p_args.get("tool_input")
        return args

    def _run_chain_if_possible(self, user_text, source_context, user_lang, api_key, base_url, model, timeout_main):
        text = str(user_text or "")
        if " and then " not in text.lower():
            return None
        parts = [p.strip() for p in re.split(r"\band then\b", text, flags=re.IGNORECASE) if p.strip()]
        if len(parts) < 2 or len(parts) > 4:
            return None
        plans = []
        for part in parts:
            p = _required_tool_plan(part, recent_messages=self._merged_history())
            if not p:
                return None
            plans.append((part, p))
        replies = []
        for part, plan in plans:
            tname, targs = plan
            rep = self._run_tool_and_format_reply(
                api_key=api_key,
                base_url=base_url,
                model=model,
                system="",
                messages=self._apply_prompt_budget([{"role": "system", "content": _language_instruction(user_lang)}]),
                user_text=part,
                user_lang=user_lang,
                source_context=source_context,
                tool_name=tname,
                tool_args=targs,
                timeout_main=timeout_main,
            )
            if rep:
                replies.append(str(rep))
        if not replies:
            return None
        return " ".join(replies[:3])

    def _trim_history(self):
        self._history = self._history[-12:]

    def _merged_history(self):
        if not self._redis_buffer.enabled:
            rows = list(self._history)
        else:
            rows = self._redis_buffer.read(max_items=12)
            if rows:
                rows = rows[-12:]
            else:
                rows = list(self._history)
        # Some providers reject history if the first non-system message is assistant.
        # Normalize to begin with a user turn and keep only valid chat roles.
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            role = str(row.get("role", "")).strip().lower()
            content = str(row.get("content", ""))
            if role not in ("user", "assistant", "system"):
                continue
            if not content.strip():
                continue
            normalized.append({"role": role, "content": content})
        while normalized and normalized[0].get("role") == "assistant":
            normalized.pop(0)
        return normalized[-12:]

    def _history_for_query(self, user_text):
        rows = self._merged_history()
        q = set(_tokenize(user_text))
        if not q:
            return rows[-8:]
        scored = []
        for row in rows:
            c = str(row.get("content", ""))
            score = len(q.intersection(set(_tokenize(c))))
            scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        picked = [r for _s, r in scored[:8]]
        # Preserve conversation order after relevance filtering.
        ordered = [r for r in rows if r in picked]
        return ordered[-8:]

    def _record_turn(self, role, content):
        self._history.append({"role": role, "content": content})
        self._trim_history()
        self._redis_buffer.append(role=role, content=content)

    def _load_soul(self):
        try:
            mtime = os.path.getmtime(self._soul_path)
        except OSError:
            return None, "SOUL.md could not be read. Restore `SOUL.md` so I can respond in the correct personality."

        if self._soul_text is not None and self._soul_mtime == mtime:
            return self._soul_text, None

        try:
            with open(self._soul_path, "r", encoding="utf-8") as f:
                soul = f.read().strip()
        except OSError:
            return None, "SOUL.md could not be read. Restore `SOUL.md` so I can respond in the correct personality."

        if not soul:
            return None, "SOUL.md is empty. Add the personality rules to `SOUL.md` so I can respond correctly."

        self._soul_text = soul
        self._soul_mtime = mtime
        return soul, None

    def respond(self, user_text, command_context=None):
        api_key, base_url, model = self._settings()
        if not (api_key and base_url and model):
            return None
        source_context = command_context if isinstance(command_context, dict) else {"source": "local", "ip": "127.0.0.1"}
        allowed, reason = validate_source_access(source_context)
        if not allowed:
            return f"Command rejected by access policy: {reason}."
        low_latency_mode = str(getattr(config, "speech_low_latency_mode", "1")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if low_latency_mode:
            model = getattr(config, "llm_fast_model", "") or model
        timeout_main = int(getattr(config, "llm_timeout_s", 18))
        timeout_fill = int(getattr(config, "llm_tool_fill_timeout_s", 10))
        timeout_fast = int(getattr(config, "llm_fast_timeout_s", 7))
        if low_latency_mode:
            timeout_main = min(timeout_main, timeout_fast)
        user_lang = _detect_user_language(user_text, source_context)
        no_llm_mode = str(getattr(config, "brain_no_llm_mode", "0")).lower() in ("1", "true", "yes", "on")
        offline_mode = str(getattr(config, "runtime_offline_mode", "0")).lower() in ("1", "true", "yes", "on")

        smalltalk = self._smalltalk_reply(user_text, user_lang)
        if smalltalk:
            self._record_turn("assistant", smalltalk)
            return smalltalk

        soul, soul_error = self._load_soul()
        if soul_error:
            return soul_error

        normalized_query = self._normalize_query(user_text)
        cached_reply = self._semantic_cache_get(f"{user_lang}:{normalized_query}")
        if cached_reply:
            return cached_reply

        history = self._history_for_query(user_text)
        system = (
            "You are JIVAN (Just Intelligent Versatile, Autonomous Nexus), a desktop voice assistant.\n"
            "\n"
            "Personality & operating principles:\n"
            + "BEGIN SOUL.md\n"
            + soul
            + "\nEND SOUL.md\n"
            + "\n\n"
            + self._base_instructions
            + "\nAvailable tools JSON:\n"
            + self._tools_prompt_cache
            + "\n\nAvailable protocols JSON:\n"
            + self._protocols_prompt_cache
            + "\n\n"
            + _language_instruction(user_lang)
            + "\n\n"
            + _telegram_owner_hint()
            + "\n\n"
            + persona_block(user_text)
        )
        mem_block = self._memory.context_block(user_text)
        if mem_block:
            system = system + "\n\n" + mem_block

        self._record_turn("user", user_text)
        messages = [{"role": "system", "content": system}] + history
        messages = self._apply_prompt_budget(messages)

        forced_plan = _required_tool_plan(user_text, recent_messages=history)
        if forced_plan:
            if offline_mode and forced_plan[0] == "mcp_execute":
                return _localized_text(
                    user_lang,
                    en="Offline mode is enabled, remote integrations are disabled.",
                    ru="Включен офлайн-режим, удаленные интеграции отключены.",
                    de="Offline-Modus ist aktiv, entfernte Integrationen sind deaktiviert.",
                )
            forced_tool_name, forced_tool_args = forced_plan
            return self._run_tool_and_format_reply(
                api_key=api_key,
                base_url=base_url,
                model=model,
                system=system,
                messages=messages,
                user_text=user_text,
                user_lang=user_lang,
                source_context=source_context,
                tool_name=forced_tool_name,
                tool_args=forced_tool_args,
                timeout_main=timeout_main,
            )

        chain_reply = self._run_chain_if_possible(
            user_text=user_text,
            source_context=source_context,
            user_lang=user_lang,
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_main=timeout_main,
        )
        if chain_reply:
            return chain_reply

        if no_llm_mode or offline_mode:
            return _localized_text(
                user_lang,
                en="No direct tool route found for that request.",
                ru="Для этого запроса не найден прямой маршрут через инструмент.",
                de="Für diese Anfrage wurde kein direkter Tool-Pfad gefunden.",
            )

        try:
            model = self._route_model(user_text, model)
            llm_started = time.perf_counter()
            self._stats["llm_calls"] += 1
            content = chat_completions(
                api_key=api_key,
                base_url=base_url,
                model=model,
                messages=messages,
                timeout_s=timeout_main,
            )
            if _latency_trace_enabled():
                print(f"[latency] llm_plan={int((time.perf_counter()-llm_started)*1000)}ms")
        except LLMError as e:
            print(f"LLM request failed: {e}")
            return "AI brain is unavailable right now."

        obj = _extract_json_object(content)
        if not obj:
            # Fallback: allow normal conversational replies even if the model
            # didn't respect the JSON-only contract. Do not attempt tool calls.
            fallback = _as_fallback_reply(content) or "Sorry, I couldn't process that."
            self._record_turn("assistant", fallback)
            self._memory.learn_turn(user_text=user_text, assistant_reply=fallback, tool_result=None)
            self._semantic_cache_set(f"{user_lang}:{normalized_query}", fallback)
            return fallback

        action = obj.get("action")
        if action == "reply":
            plan = _required_tool_plan(user_text, recent_messages=self._merged_history())
            if plan:
                forced_tool_name, forced_tool_args = plan
                return self._run_tool_and_format_reply(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    system=system,
                    messages=messages,
                    user_text=user_text,
                    user_lang=user_lang,
                    source_context=source_context,
                    tool_name=forced_tool_name,
                    tool_args=forced_tool_args,
                    timeout_main=timeout_main,
                )
            reply = obj.get("reply", "")
            self._record_turn("assistant", reply)
            self._memory.learn_turn(user_text=user_text, assistant_reply=reply, tool_result=None)
            self._semantic_cache_set(f"{user_lang}:{normalized_query}", reply)
            return reply

        if action == "tool":
            tool_name = obj.get("tool_name")
            tool_args = obj.get("tool_args", {}) or {}
            if not isinstance(tool_args, dict):
                tool_args = {}
            tool_args = self._deterministic_fill_tool_args(
                tool_name=tool_name,
                user_text=user_text,
                tool_args=tool_args,
            )

            spec = get_tool_spec(tool_name)
            if spec:
                expected_args = spec.get("args") or {}
                required_args = spec.get("required")
                if isinstance(required_args, list):
                    arg_keys = required_args
                else:
                    arg_keys = list(expected_args.keys())
                missing = []
                for k in arg_keys:
                    if k not in tool_args or tool_args.get(k) in ("", None):
                        missing.append(k)
                if missing:
                    # Ask the LLM to fill tool_args (without changing tool_name).
                    fill_system = (
                        "Return ONLY a JSON object for tool_args. "
                        "Do not include any extra keys. "
                        "If an arg is unknown, set it to an empty string."
                    )
                    try:
                        filled = chat_completions(
                            api_key=api_key,
                            base_url=base_url,
                            model=model,
                            messages=[
                                {"role": "system", "content": fill_system},
                                {
                                    "role": "user",
                                    "content": json.dumps(
                                        {
                                            "user_text": user_text,
                                            "tool_name": tool_name,
                                            "tool_spec": spec,
                                            "current_tool_args": tool_args,
                                        }
                                    ),
                                },
                            ],
                            timeout_s=timeout_fill,
                        )
                        filled_obj = _extract_json_object(filled) or {}
                        if isinstance(filled_obj, dict):
                            tool_args = {**tool_args, **filled_obj}
                    except LLMError as e:
                        print(f"LLM tool-arg fill failed: {e}")
                        pass

            return self._run_tool_and_format_reply(
                api_key=api_key,
                base_url=base_url,
                model=model,
                system=system,
                messages=messages,
                user_text=user_text,
                user_lang=user_lang,
                source_context=source_context,
                tool_name=tool_name,
                tool_args=tool_args,
                timeout_main=timeout_main,
            )

        return "AI brain returned an unsupported action."

    def _run_tool_and_format_reply(
        self,
        *,
        api_key,
        base_url,
        model,
        system,
        messages,
        user_text,
        user_lang,
        source_context,
        tool_name,
        tool_args,
        timeout_main,
    ):
        if self._cacheable_tool(tool_name):
            cached = self._tool_cache_get(tool_name, tool_args)
            if isinstance(cached, dict):
                tool_result = cached
            else:
                tool_result = None
        else:
            tool_result = None

        if tool_result is None:
            tool_result = {"ok": False}
            last_exc = None
            for _attempt in range(2):
                try:
                    tool_started = time.perf_counter()
                    self._stats["tool_calls"] += 1
                    tool_result = run_tool(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        user_text=user_text,
                        source_context=source_context,
                        assistant=self._assistant,
                        wolfram_fn=self._wolfram_fn,
                    )
                    if _latency_trace_enabled():
                        print(f"[latency] tool_exec={int((time.perf_counter()-tool_started)*1000)}ms tool={tool_name}")
                    break
                except Exception as e:
                    last_exc = e
                    time.sleep(0.1)
            if not isinstance(tool_result, dict) or (not tool_result.get("ok") and last_exc is not None):
                return "Sorry, I couldn't run that tool."
            if self._cacheable_tool(tool_name) and isinstance(tool_result, dict) and tool_result.get("ok"):
                self._tool_cache_set(tool_name, tool_args, tool_result)

        followup_payload = {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": tool_result,
        }
        fast_reply = _fast_tool_reply(tool_name=tool_name, tool_result=tool_result, user_lang=user_lang)
        if fast_reply:
            self._record_turn("assistant", fast_reply)
            self._memory.learn_turn(user_text=user_text, assistant_reply=fast_reply, tool_result=tool_result)
            replay_event("tool_fast_reply", {"tool": tool_name, "reply": fast_reply})
            return fast_reply
        if isinstance(tool_result, dict) and not tool_result.get("ok"):
            error_code = tool_result.get("error_code", "execution_failed")
            details = tool_result.get("details", "")
            msg = humanize(error_code, details)
            self._record_turn("assistant", msg)
            self._memory.learn_turn(user_text=user_text, assistant_reply=msg, tool_result=tool_result)
            replay_event("tool_error", {"tool": tool_name, "error_code": error_code})
            return msg
        followup = (
            "You just called a tool. Write the final user-facing response in JIVAN voice and SOUL.md style.\n"
            "Rules:\n"
            "- Do not dump raw JSON unless the user asked for it.\n"
            "- If tool_result.ok is false, explain what you need from the user.\n"
            "- If confirmation is required, ask for confirmation.\n"
            "- Be concise.\n"
            + _language_instruction(user_lang)
            + "\n"
            + persona_block(user_text, tool_result=tool_result)
            + "\n"
            "DATA:\n"
            + json.dumps(followup_payload, ensure_ascii=False)
            + "\nReturn ONLY JSON: "
            + '{"action":"reply","reply":"..."}'
        )

        try:
            llm2_started = time.perf_counter()
            content2 = chat_completions(
                api_key=api_key,
                base_url=base_url,
                model=model,
                messages=messages + [{"role": "user", "content": followup}],
                timeout_s=timeout_main,
            )
            if _latency_trace_enabled():
                print(f"[latency] llm_format={int((time.perf_counter()-llm2_started)*1000)}ms")
        except LLMError as e:
            print(f"LLM follow-up failed: {e}")
            return str(tool_result)

        obj2 = _extract_json_object(content2)
        if obj2 and obj2.get("action") == "reply":
            reply2 = obj2.get("reply", "")
            self._record_turn("assistant", reply2)
            self._memory.learn_turn(user_text=user_text, assistant_reply=reply2, tool_result=tool_result)
            return reply2

        fallback2 = _as_fallback_reply(content2) or str(tool_result)
        self._record_turn("assistant", fallback2)
        self._memory.learn_turn(user_text=user_text, assistant_reply=fallback2, tool_result=tool_result)
        return fallback2
