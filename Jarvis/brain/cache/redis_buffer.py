import json
import time

from Jarvis.config import config


def _as_bool(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


class RedisConversationBuffer:
    def __init__(self):
        self.enabled = _as_bool(getattr(config, "redis_enabled", "0"))
        self.url = getattr(config, "redis_url", "redis://localhost:6379/0")
        self.key = getattr(config, "redis_session_key", "jivan:session:default")
        self.ttl_s = int(getattr(config, "redis_history_ttl_s", 86400))
        self.max_items = int(getattr(config, "redis_max_items", 24))
        self._client = self._init_client()
        self._retry_ts = 0.0
        self._health_cache = None
        self._health_cache_ts = 0.0

    def _init_client(self):
        if not self.enabled:
            return None
        try:
            import redis  # type: ignore
        except Exception:
            return None
        try:
            return redis.Redis.from_url(self.url, decode_responses=True)
        except Exception:
            return None

    def _ensure_client(self, *, force=False):
        if self._client is not None:
            return self._client
        if not self.enabled:
            return None
        now = time.time()
        if not force and (now - self._retry_ts) < 5:
            return None
        self._retry_ts = now
        self._client = self._init_client()
        return self._client

    def health_check(self, force=False):
        now = time.time()
        if not force and self._health_cache is not None and (now - self._health_cache_ts) < 30:
            return dict(self._health_cache)
        if not self.enabled:
            status = {"enabled": False, "ok": False, "status": "disabled"}
        elif not self._ensure_client(force=force):
            status = {"enabled": True, "ok": False, "status": "client_unavailable"}
        else:
            try:
                self._client.ping()
                status = {"enabled": True, "ok": True, "status": "connected"}
            except Exception as e:
                self._client = None
                status = {"enabled": True, "ok": False, "status": "connect_failed", "details": str(e)}
        self._health_cache = status
        self._health_cache_ts = now
        return dict(status)

    def append(self, role, content):
        client = self._ensure_client()
        if not client:
            return False
        row = {"role": str(role or ""), "content": str(content or "")}
        try:
            p = client.pipeline()
            p.rpush(self.key, json.dumps(row, ensure_ascii=False))
            p.ltrim(self.key, -self.max_items, -1)
            p.expire(self.key, self.ttl_s)
            p.execute()
            return True
        except Exception:
            # Redis can restart; retry once with a fresh client.
            self._client = None
            client = self._ensure_client(force=True)
            if not client:
                return False
            try:
                p = client.pipeline()
                p.rpush(self.key, json.dumps(row, ensure_ascii=False))
                p.ltrim(self.key, -self.max_items, -1)
                p.expire(self.key, self.ttl_s)
                p.execute()
                return True
            except Exception:
                self._client = None
                return False

    def read(self, max_items=None):
        client = self._ensure_client()
        if not client:
            return []
        count = int(max_items or self.max_items)
        try:
            rows = client.lrange(self.key, -count, -1)
        except Exception:
            self._client = None
            return []
        out = []
        for row in rows:
            try:
                obj = json.loads(row)
            except Exception:
                continue
            if isinstance(obj, dict) and obj.get("role") and obj.get("content") is not None:
                out.append({"role": str(obj["role"]), "content": str(obj["content"])})
        return out
