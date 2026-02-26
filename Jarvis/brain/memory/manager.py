import datetime
import json
import os
import re
import time
import uuid
import queue
import threading

from Jarvis.config import config


def _now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _tokenize(text):
    return [t for t in re.split(r"[^a-zA-Z0-9_]+", str(text or "").lower()) if len(t) > 1]


def _is_sensitive(text):
    t = str(text or "").lower()
    sensitive_markers = (
        "password",
        "passcode",
        "secret",
        "private key",
        "api key",
        "token",
        "credit card",
        "ssn",
        "otp",
    )
    return any(m in t for m in sensitive_markers)


class MemoryManager:
    def __init__(self):
        self.enabled = str(getattr(config, "mem0_enabled", "0")).lower() in ("1", "true", "yes", "on")
        self.api_key = getattr(config, "mem0_api_key", "") or ""
        self.base_url = getattr(config, "mem0_base_url", "https://api.mem0.ai/v1")
        self.user_id = getattr(config, "mem0_user_id", "default_user")
        self.collection = getattr(config, "mem0_collection", "jivan")
        self.max_items = int(getattr(config, "mem0_max_context_items", 4))
        self.read_timeout_ms = int(getattr(config, "mem0_read_timeout_ms", 350))
        self.write_mode = str(getattr(config, "mem0_write_mode", "safe")).lower()
        self.async_write = str(getattr(config, "mem0_async_write", "0")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self.redact_sensitive = str(getattr(config, "mem0_redact_sensitive", "1")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        local_path = getattr(config, "mem0_local_store_path", "") or ""
        if not local_path:
            local_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "memories_local.jsonl")
            )
        self.local_path = local_path
        self._sdk_client = self._init_sdk_client()
        self._sdk_retry_ts = 0.0
        self._health_cache = None
        self._health_cache_ts = 0.0
        self._write_queue = queue.Queue()
        self._worker = None
        if self.enabled and self.write_mode != "off" and self.async_write:
            self._worker = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker.start()

    def _init_sdk_client(self):
        if not self.api_key:
            return None
        try:
            from mem0 import MemoryClient  # type: ignore
        except Exception:
            return None
        try:
            # Dashboard quick-start uses api_key-only initialization.
            return MemoryClient(api_key=self.api_key)
        except Exception:
            return None

    def _ensure_sdk_client(self, *, force=False):
        if self._sdk_client is not None:
            return self._sdk_client
        if not self.api_key:
            return None
        now = time.time()
        if not force and (now - self._sdk_retry_ts) < 15:
            return None
        self._sdk_retry_ts = now
        self._sdk_client = self._init_sdk_client()
        return self._sdk_client

    def retrieve_context(self, query):
        if not self.enabled:
            return []
        self._ensure_sdk_client()
        remote_items = self._retrieve_remote_with_budget(query) if self._sdk_client else []
        local_items = self._retrieve_local(query)
        merged = []
        seen = set()
        for row in (remote_items + local_items):
            if not isinstance(row, dict):
                continue
            text = str(row.get("text", "")).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            score = self._score_relevance(query=query, text=text)
            merged.append((score, row))
        merged.sort(key=lambda x: x[0], reverse=True)
        return [r for _s, r in merged[: self.max_items]]

    def _retrieve_remote_with_budget(self, query):
        budget = max(10, int(self.read_timeout_ms))
        out = {"rows": []}

        def _run():
            out["rows"] = self._retrieve_remote(query)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=float(budget) / 1000.0)
        if t.is_alive():
            return []
        rows = out.get("rows")
        return rows if isinstance(rows, list) else []

    def _score_relevance(self, *, query, text):
        q_tokens = set(_tokenize(query))
        t_tokens = set(_tokenize(text))
        if not q_tokens:
            return 0.0
        overlap = len(q_tokens.intersection(t_tokens))
        ratio = float(overlap) / float(max(1, len(q_tokens)))
        return ratio

    def health_check(self, force=False):
        now = time.time()
        if not force and self._health_cache is not None and (now - self._health_cache_ts) < 30:
            return dict(self._health_cache)

        if not self.enabled:
            status = {"enabled": False, "ok": False, "status": "disabled"}
            self._health_cache = status
            self._health_cache_ts = now
            return dict(status)

        if not self.api_key:
            status = {"enabled": True, "ok": False, "status": "missing_api_key"}
            self._health_cache = status
            self._health_cache_ts = now
            return dict(status)

        self._ensure_sdk_client(force=True)
        if not self._sdk_client:
            status = {"enabled": True, "ok": False, "status": "sdk_unavailable"}
            self._health_cache = status
            self._health_cache_ts = now
            return dict(status)

        filters = {"OR": [{"user_id": self.user_id}]}
        try:
            self._sdk_client.search("__mem0_health_check__", version="v2", filters=filters)
            status = {"enabled": True, "ok": True, "status": "connected"}
        except Exception as e:
            status = {"enabled": True, "ok": False, "status": "connect_failed", "details": str(e)}

        self._health_cache = status
        self._health_cache_ts = now
        return dict(status)

    def context_block(self, query):
        rows = self.retrieve_context(query)
        if not rows:
            return ""
        lines = []
        for i, it in enumerate(rows, 1):
            txt = str(it.get("text", "")).strip()
            if not txt:
                continue
            lines.append(f"{i}. {txt}")
        if not lines:
            return ""
        return "Known user memory (use when relevant, do not invent):\n" + "\n".join(lines)

    def learn_turn(self, *, user_text="", assistant_reply="", tool_result=None):
        if not self.enabled:
            return
        if self.write_mode == "off":
            return
        if self.async_write:
            try:
                self._write_queue.put_nowait(
                    {"user_text": user_text, "assistant_reply": assistant_reply, "tool_result": tool_result}
                )
                return
            except Exception:
                pass
        self._learn_turn_sync(user_text=user_text, assistant_reply=assistant_reply, tool_result=tool_result)

    def _worker_loop(self):
        while True:
            try:
                item = self._write_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._learn_turn_sync(
                    user_text=item.get("user_text", ""),
                    assistant_reply=item.get("assistant_reply", ""),
                    tool_result=item.get("tool_result"),
                )
            except Exception:
                pass
            finally:
                self._write_queue.task_done()

    def _learn_turn_sync(self, *, user_text="", assistant_reply="", tool_result=None):
        if not self.enabled or self.write_mode == "off":
            return
        self._ensure_sdk_client()

        candidates = self._extract_candidates(user_text=user_text, assistant_reply=assistant_reply, tool_result=tool_result)
        # Preferred path: send conversation snippets to Mem0 SDK directly.
        if self._sdk_client and self.write_mode in ("safe", "full"):
            self._save_remote_conversation(user_text=user_text, assistant_reply=assistant_reply)

        for c in candidates:
            text = c.get("text", "").strip()
            if not text:
                continue
            if self.redact_sensitive and _is_sensitive(text):
                continue
            self._save_memory(text=text, category=c.get("category", "preference"), tags=c.get("tags") or [])

    def _extract_candidates(self, *, user_text, assistant_reply, tool_result):
        text = str(user_text or "").strip()
        lowered = text.lower()
        out = []

        patterns = [
            (r"\bmy name is ([a-zA-Z][a-zA-Z\-\s]{1,40})", "profile", ["identity"]),
            (r"\bi am ([a-zA-Z][a-zA-Z\-\s]{1,40})", "profile", ["identity"]),
            (r"\bi work as ([a-zA-Z][a-zA-Z\-\s]{1,60})", "profile", ["work"]),
            (r"\bi prefer ([^.,;]{2,80})", "preference", ["preference"]),
            (r"\bi like ([^.,;]{2,80})", "preference", ["preference"]),
            (r"\bremember that ([^.,;]{2,120})", "long_term", ["explicit_memory"]),
        ]

        for pat, cat, tags in patterns:
            m = re.search(pat, lowered)
            if not m:
                continue
            capture = m.group(1).strip()
            if len(capture) < 2:
                continue
            if pat.startswith(r"\bmy name is"):
                txt = f"User name is {capture.title()}."
            elif pat.startswith(r"\bi am "):
                txt = f"User identity note: {capture}."
            elif pat.startswith(r"\bi work as"):
                txt = f"User works as {capture}."
            elif pat.startswith(r"\bi prefer"):
                txt = f"User prefers {capture}."
            elif pat.startswith(r"\bi like"):
                txt = f"User likes {capture}."
            else:
                txt = f"User asked to remember: {capture}."
            out.append({"text": txt, "category": cat, "tags": tags})

        # Optional extraction from explicit successful tool operations.
        tr = tool_result if isinstance(tool_result, dict) else {}
        if tr.get("ok") and tr.get("tool_name") == "run_protocol":
            proto = tr.get("protocol") or ""
            if proto:
                out.append(
                    {
                        "text": f"User executed protocol {proto}.",
                        "category": "operational",
                        "tags": ["protocol_usage"],
                    }
                )
        return out

    def _save_memory(self, *, text, category, tags):
        payload = {
            "id": str(uuid.uuid4()),
            "text": text.strip(),
            "category": category,
            "tags": list(tags or []),
            "user_id": self.user_id,
            "collection": self.collection,
            "created_at": _now_iso(),
        }
        # Keep a deterministic local mirror so short-term personalization still works
        # even if remote Mem0 indexing is delayed or returns weak matches.
        self._save_local(payload)
        if self.api_key and self.write_mode in ("safe", "full"):
            ok = self._save_remote(payload)
            if ok:
                return

    def _save_local(self, payload):
        path = self.local_path
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError:
            return False
        return True

    def _retrieve_local(self, query):
        path = self.local_path
        if not os.path.exists(path):
            return []
        q_tokens = set(_tokenize(query))
        rows = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    if row.get("user_id") != self.user_id:
                        continue
                    text = str(row.get("text", ""))
                    tks = set(_tokenize(text))
                    overlap = len(q_tokens.intersection(tks)) if q_tokens else 0
                    score = overlap
                    # Slight freshness boost.
                    if row.get("created_at"):
                        score += 0.2
                    rows.append((score, row))
        except OSError:
            return []

        rows.sort(key=lambda x: x[0], reverse=True)
        # If query has no overlap, still return latest few memories.
        if rows and rows[0][0] <= 0:
            return [r for _s, r in rows[-self.max_items :]][::-1]
        return [r for _s, r in rows[: self.max_items]]

    def _save_remote_conversation(self, *, user_text, assistant_reply):
        if not self._sdk_client:
            return False
        user_text = str(user_text or "").strip()
        assistant_reply = str(assistant_reply or "").strip()
        messages = []
        if user_text and not (self.redact_sensitive and _is_sensitive(user_text)):
            messages.append({"role": "user", "content": user_text})
        if assistant_reply and not (self.redact_sensitive and _is_sensitive(assistant_reply)):
            messages.append({"role": "assistant", "content": assistant_reply})
        if not messages:
            return False
        try:
            # Mem0 official quick-start signature.
            self._sdk_client.add(messages, user_id=self.user_id)
            return True
        except Exception:
            return False

    def _save_remote(self, payload):
        if not self._sdk_client:
            return False
        text = str(payload.get("text") or "").strip()
        if not text:
            return False
        if self.redact_sensitive and _is_sensitive(text):
            return False
        messages = [{"role": "user", "content": text}]
        try:
            self._sdk_client.add(messages, user_id=self.user_id)
            return True
        except Exception:
            return False

    def _retrieve_remote(self, query):
        if not self._sdk_client:
            return []
        filters = {"OR": [{"user_id": self.user_id}]}
        try:
            data = self._sdk_client.search(query, version="v2", filters=filters)
        except Exception:
            return []

        # SDK may return list or dict; support multiple shapes.
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("results") or data.get("items") or data.get("memories") or []
        else:
            items = []
        if not isinstance(items, list):
            return []

        out = []
        for it in items:
            if not isinstance(it, dict):
                continue
            text = (
                it.get("memory")
                or it.get("text")
                or (it.get("data", {}) if isinstance(it.get("data"), dict) else {}).get("text")
                or ""
            )
            text = str(text).strip()
            if not text:
                continue
            out.append({"text": text, "category": it.get("category", ""), "tags": it.get("tags") or []})
        return out[: self.max_items]
