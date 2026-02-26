import importlib.util
import sys
import tempfile
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


def _install_stub_config(state_path):
    if "Jarvis" not in sys.modules:
        sys.modules["Jarvis"] = types.ModuleType("Jarvis")
    config_pkg = types.ModuleType("Jarvis.config")
    config_mod = types.ModuleType("Jarvis.config.config")
    config_mod.telegram_state_path = str(state_path)
    config_pkg.config = config_mod
    sys.modules["Jarvis.config"] = config_pkg
    sys.modules["Jarvis.config.config"] = config_mod


class TelegramStateTests(unittest.TestCase):
    def test_update_from_updates_and_send(self):
        with tempfile.TemporaryDirectory() as td:
            state_file = Path(td) / "tg_state.json"
            _install_stub_config(state_file)
            mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "telegram_state.py", "tg_state_mod")
            store = mod.TelegramStateStore()

            updates_payload = {
                "result": [
                    {
                        "message": {
                            "message_id": 10,
                            "chat": {"id": 12345, "type": "private"},
                        }
                    }
                ]
            }
            self.assertTrue(store.update_from_updates_result(updates_payload))
            self.assertEqual(store.get_primary_chat_id(), 12345)
            self.assertEqual(store.get_last_message_id(12345), 10)

            send_payload = {
                "result": {
                    "message_id": 11,
                    "chat": {"id": 12345, "type": "private"},
                }
            }
            self.assertTrue(store.update_from_send_message_result(send_payload))
            self.assertEqual(store.get_last_message_id(12345), 11)


if __name__ == "__main__":
    unittest.main()
