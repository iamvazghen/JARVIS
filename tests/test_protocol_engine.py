import importlib.util
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


engine_mod = _load_module(Path("Jarvis") / "protocols" / "engine.py", "protocol_engine")
monday_mod = _load_module(Path("Jarvis") / "protocols" / "monday.py", "protocol_monday")
monday_morning_mod = _load_module(
    Path("Jarvis") / "protocols" / "monday_morning.py", "protocol_monday_morning"
)


class ProtocolEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = engine_mod.ProtocolEngine()
        self.modules = [monday_mod, monday_morning_mod]

    def test_trigger_resolution_prefers_specific(self):
        p = self.engine.resolve_protocol(self.modules, user_text="run protocol monday morning")
        self.assertIsNotNone(p)
        self.assertEqual(p.spec().get("name"), "monday_morning")

    def test_trigger_resolution_with_additional_verbs(self):
        p = self.engine.resolve_protocol(self.modules, user_text="start protocol monday morning")
        self.assertIsNotNone(p)
        self.assertEqual(p.spec().get("name"), "monday_morning")

    def test_confirmation_required_for_side_effects(self):
        res = self.engine.run(self.modules, name="monday", user_text="run protocol monday", confirm=False)
        self.assertFalse(res.get("ok"))
        self.assertEqual(res.get("error_code"), "confirmation_required")

    def test_confirmed_run_returns_action(self):
        res = self.engine.run(self.modules, name="monday", user_text="run protocol monday", confirm=True)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("action"), "shutdown_app")

    def test_dry_run_returns_steps(self):
        res = self.engine.run(
            self.modules,
            name="monday_morning",
            user_text="run protocol monday morning",
            confirm=True,
            dry_run=True,
        )
        self.assertTrue(res.get("ok"))
        self.assertTrue(res.get("dry_run"))
        self.assertTrue(isinstance(res.get("steps"), list))

    def test_chain_step_executes_nested_protocol(self):
        chain = types.SimpleNamespace()

        def chain_spec():
            return {
                "name": "chain_shutdown",
                "aliases": [],
                "side_effects": True,
                "confirmation_policy": "if_side_effects",
                "requires_confirmation": True,
                "triggers": ["chain shutdown"],
                "steps": [{"type": "protocol", "name": "monday"}],
            }

        chain.spec = chain_spec
        modules = [monday_mod, chain]
        res = self.engine.run(modules, name="chain_shutdown", user_text="chain shutdown", confirm=True)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("action"), "shutdown_app")


if __name__ == "__main__":
    unittest.main()
