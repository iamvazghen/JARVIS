import importlib.util
import os
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


class AuditReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = str(Path(__file__).resolve().parents[1])
        cls.tool_mod = _load_module(Path("Jarvis") / "audit" / "tool_usage.py", "audit_tool_mod")
        cls.sec_mod = _load_module(Path("Jarvis") / "audit" / "security.py", "audit_sec_mod")

    def test_tool_usage_report_shape(self):
        report = self.tool_mod.generate_tool_usage_report(self.repo_root)
        self.assertIn("status", report)
        self.assertIn("missing_tools", report)
        self.assertIn("failed_routes", report)

    def test_security_report_shape(self):
        report = self.sec_mod.generate_security_report(self.repo_root)
        self.assertIn("status", report)
        self.assertIn("findings", report)
        self.assertIn("env_hygiene", report)
        self.assertTrue(os.path.exists(os.path.join(self.repo_root, ".env.example")))


if __name__ == "__main__":
    unittest.main()
