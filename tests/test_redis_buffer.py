import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _load_module(relative_path, module_name):
    repo_root = Path(__file__).resolve().parents[1]
    mod_path = repo_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, str(mod_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _install_stub_config(enabled="1"):
    if "Jarvis" not in sys.modules:
        sys.modules["Jarvis"] = types.ModuleType("Jarvis")
    config_pkg = types.ModuleType("Jarvis.config")
    config_mod = types.ModuleType("Jarvis.config.config")
    config_mod.redis_enabled = enabled
    config_mod.redis_url = "redis://localhost:6379/0"
    config_mod.redis_session_key = "jivan:session:test"
    config_mod.redis_history_ttl_s = 3600
    config_mod.redis_max_items = 5
    config_pkg.config = config_mod
    sys.modules["Jarvis.config"] = config_pkg
    sys.modules["Jarvis.config.config"] = config_mod


def _install_stub_redis():
    redis_mod = types.ModuleType("redis")

    class _Pipe:
        def __init__(self, owner):
            self.owner = owner
            self.ops = []

        def rpush(self, key, val):
            self.ops.append(("rpush", key, val))
            return self

        def ltrim(self, key, a, b):
            self.ops.append(("ltrim", key, a, b))
            return self

        def expire(self, key, ttl):
            self.ops.append(("expire", key, ttl))
            return self

        def execute(self):
            for op in self.ops:
                if op[0] == "rpush":
                    self.owner.data.setdefault(op[1], []).append(op[2])
                elif op[0] == "ltrim":
                    key, a, b = op[1], op[2], op[3]
                    rows = self.owner.data.get(key, [])
                    self.owner.data[key] = rows[a if a != 0 else None : b + 1 if b != -1 else None]
            return True

    class _Client:
        def __init__(self):
            self.data = {}
            self.fail_once = False

        def ping(self):
            return True

        def pipeline(self):
            if self.fail_once:
                self.fail_once = False
                raise RuntimeError("transient redis failure")
            return _Pipe(self)

        def lrange(self, key, a, b):
            rows = self.data.get(key, [])
            return rows[a if a != 0 else None : b + 1 if b != -1 else None]

    class Redis:
        _last_client = None

        @staticmethod
        def from_url(url, decode_responses=True):
            c = _Client()
            Redis._last_client = c
            return c

    redis_mod.Redis = Redis
    sys.modules["redis"] = redis_mod
    return Redis


class RedisBufferTests(unittest.TestCase):
    def test_append_and_read(self):
        _install_stub_config(enabled="1")
        _install_stub_redis()
        mod = _load_module(Path("Jarvis") / "brain" / "cache" / "redis_buffer.py", "redis_buffer_mod")
        buf = mod.RedisConversationBuffer()
        self.assertTrue(buf.health_check(force=True).get("ok"))
        self.assertTrue(buf.append("user", "hello"))
        self.assertTrue(buf.append("assistant", "hi"))
        rows = buf.read()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].get("role"), "user")

    def test_append_retries_after_transient_failure(self):
        _install_stub_config(enabled="1")
        Redis = _install_stub_redis()
        mod = _load_module(Path("Jarvis") / "brain" / "cache" / "redis_buffer.py", "redis_buffer_mod_retry")
        buf = mod.RedisConversationBuffer()
        # Make the first pipeline call fail, then verify retry path writes.
        Redis._last_client.fail_once = True
        self.assertTrue(buf.append("user", "retry hello"))
        rows = buf.read()
        self.assertTrue(any(r.get("content") == "retry hello" for r in rows))


if __name__ == "__main__":
    unittest.main()
