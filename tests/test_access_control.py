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


def _install_stub_config():
    if "Jarvis" not in sys.modules:
        sys.modules["Jarvis"] = types.ModuleType("Jarvis")
    config_pkg = types.ModuleType("Jarvis.config")
    config_mod = types.ModuleType("Jarvis.config.config")
    config_mod.security_enforce_source_allowlist = "1"
    config_mod.security_allowed_source_ips = "127.0.0.1,100.100.5.2"
    config_mod.security_require_tailscale_for_remote = "1"
    config_mod.security_allowed_tailscale_cidrs = "100.64.0.0/10"
    config_mod.security_allowed_telegram_user_ids = "12345"
    config_mod.security_allowed_telegram_usernames = "iamvazghen"
    config_pkg.config = config_mod
    sys.modules["Jarvis.config"] = config_pkg
    sys.modules["Jarvis.config.config"] = config_mod


class AccessControlTests(unittest.TestCase):
    def test_remote_non_tailscale_denied(self):
        _install_stub_config()
        mod = _load_module(Path("Jarvis") / "security" / "access_control.py", "access_control_mod")
        ok, reason = mod.validate_source_access({"source": "http", "ip": "8.8.8.8"})
        self.assertFalse(ok)
        self.assertEqual(reason, "remote_source_not_in_tailscale_range")

    def test_telegram_identity_allowlist(self):
        _install_stub_config()
        mod = _load_module(Path("Jarvis") / "security" / "access_control.py", "access_control_mod2")
        ok, _ = mod.validate_source_access(
            {"source": "telegram", "ip": "100.100.5.2", "telegram_user_id": "12345"}
        )
        self.assertTrue(ok)
        ok2, reason2 = mod.validate_source_access(
            {"source": "telegram", "ip": "100.100.5.2", "telegram_user_id": "999"}
        )
        self.assertFalse(ok2)
        self.assertEqual(reason2, "telegram_identity_not_allowlisted")

    def test_telegram_allowed_without_ip(self):
        _install_stub_config()
        mod = _load_module(Path("Jarvis") / "security" / "access_control.py", "access_control_mod3")
        ok, reason = mod.validate_source_access({"source": "telegram", "telegram_username": "iamvazghen"})
        self.assertTrue(ok)
        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()
