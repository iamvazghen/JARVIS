import importlib.util
import os
import tempfile
import types
import unittest
import sys
from pathlib import Path


def _load_module(relative_path, module_name):
    repo_root = Path(__file__).resolve().parents[1]
    mod_path = repo_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, str(mod_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _install_stub_config(tmp_path):
    if "Jarvis" not in sys.modules:
        sys.modules["Jarvis"] = types.ModuleType("Jarvis")
    config_pkg = types.ModuleType("Jarvis.config")
    config_mod = types.ModuleType("Jarvis.config.config")
    config_mod.mem0_enabled = "1"
    config_mod.mem0_api_key = ""
    config_mod.mem0_base_url = "https://api.mem0.ai/v1"
    config_mod.mem0_user_id = "tester"
    config_mod.mem0_collection = "jivan"
    config_mod.mem0_write_mode = "safe"
    config_mod.mem0_max_context_items = 4
    config_mod.mem0_redact_sensitive = "1"
    config_mod.mem0_local_store_path = str(tmp_path)
    config_pkg.config = config_mod
    sys.modules["Jarvis.config"] = config_pkg
    sys.modules["Jarvis.config.config"] = config_mod
    return config_mod


def _install_stub_mem0():
    mem0_mod = types.ModuleType("mem0")

    class MemoryClient:
        instances = []

        def __init__(self, api_key=""):
            self.api_key = api_key
            self.add_calls = []
            self.search_calls = []
            self.search_response = [{"memory": "User prefers vegetarian meals."}]
            MemoryClient.instances.append(self)

        def add(self, messages, user_id=""):
            self.add_calls.append({"messages": messages, "user_id": user_id})
            return {"status": "ok"}

        def search(self, query, version="v2", filters=None):
            self.search_calls.append({"query": query, "version": version, "filters": filters})
            return self.search_response

    mem0_mod.MemoryClient = MemoryClient
    sys.modules["mem0"] = mem0_mod
    return MemoryClient


class MemoryManagerTests(unittest.TestCase):
    def test_learn_and_retrieve(self):
        with tempfile.TemporaryDirectory() as td:
            store_path = Path(td) / "mem.jsonl"
            _install_stub_config(store_path)
            mod = _load_module(Path("Jarvis") / "brain" / "memory" / "manager.py", "mem_manager_mod_a")
            mgr = mod.MemoryManager()
            mgr.learn_turn(user_text="my name is Tony", assistant_reply="Nice to meet you", tool_result=None)
            ctx = mgr.retrieve_context("what is my name")
            self.assertTrue(isinstance(ctx, list))
            self.assertTrue(any("User name is Tony." in x.get("text", "") for x in ctx))

    def test_sensitive_memory_is_not_saved(self):
        with tempfile.TemporaryDirectory() as td:
            store_path = Path(td) / "mem.jsonl"
            _install_stub_config(store_path)
            mod = _load_module(Path("Jarvis") / "brain" / "memory" / "manager.py", "mem_manager_mod_b")
            mgr = mod.MemoryManager()
            mgr.learn_turn(user_text="remember that my password is 123456", assistant_reply="", tool_result=None)
            rows = mgr.retrieve_context("password")
            self.assertEqual(rows, [])

    def test_protocol_usage_memory(self):
        with tempfile.TemporaryDirectory() as td:
            store_path = Path(td) / "mem.jsonl"
            _install_stub_config(store_path)
            mod = _load_module(Path("Jarvis") / "brain" / "memory" / "manager.py", "mem_manager_mod_c")
            mgr = mod.MemoryManager()
            mgr.learn_turn(
                user_text="run protocol house party",
                assistant_reply="Done",
                tool_result={"ok": True, "tool_name": "run_protocol", "protocol": "protocol_house_party"},
            )
            ctx = mgr.retrieve_context("protocol")
            self.assertTrue(any("executed protocol" in x.get("text", "").lower() for x in ctx))

    def test_sdk_add_and_search_are_used_when_available(self):
        with tempfile.TemporaryDirectory() as td:
            store_path = Path(td) / "mem.jsonl"
            cfg = _install_stub_config(store_path)
            cfg.mem0_api_key = "m0-test"
            MemoryClient = _install_stub_mem0()
            mod = _load_module(Path("Jarvis") / "brain" / "memory" / "manager.py", "mem_manager_mod_d")
            mgr = mod.MemoryManager()
            mgr.learn_turn(user_text="I prefer dark roast coffee", assistant_reply="Noted", tool_result=None)
            ctx = mgr.retrieve_context("what coffee do I like")
            self.assertTrue(len(MemoryClient.instances) >= 1)
            client = MemoryClient.instances[-1]
            self.assertTrue(len(client.add_calls) >= 1)
            self.assertTrue(len(client.search_calls) >= 1)
            self.assertTrue(any("vegetarian" in x.get("text", "").lower() for x in ctx))

    def test_health_check_connected_with_sdk(self):
        with tempfile.TemporaryDirectory() as td:
            store_path = Path(td) / "mem.jsonl"
            cfg = _install_stub_config(store_path)
            cfg.mem0_api_key = "m0-test"
            _install_stub_mem0()
            mod = _load_module(Path("Jarvis") / "brain" / "memory" / "manager.py", "mem_manager_mod_e")
            mgr = mod.MemoryManager()
            h = mgr.health_check(force=True)
            self.assertTrue(h.get("enabled"))
            self.assertTrue(h.get("ok"))
            self.assertEqual(h.get("status"), "connected")


if __name__ == "__main__":
    unittest.main()
