import importlib.util
import json
import tempfile
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


loader_mod = _load_module(Path("Jarvis") / "protocols" / "custom_loader.py", "custom_loader_mod")
engine_mod = _load_module(Path("Jarvis") / "protocols" / "engine.py", "protocol_engine_mod")
monday_mod = _load_module(Path("Jarvis") / "protocols" / "monday.py", "protocol_monday_mod")


class CustomProtocolLoaderTests(unittest.TestCase):
    def test_load_single_protocol_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "demo.json"
            p.write_text(
                json.dumps(
                    {
                        "name": "demo_proto",
                        "triggers": ["run demo proto"],
                        "side_effects": True,
                        "requires_confirmation": True,
                        "steps": [{"type": "action", "name": "shutdown_app"}],
                    }
                ),
                encoding="utf-8",
            )
            loaded = loader_mod.load_file_protocols(custom_dir=str(td))
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].spec().get("name"), "demo_proto")

    def test_placeholder_rendering(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "demo.json"
            p.write_text(
                json.dumps(
                    {
                        "name": "templated_proto",
                        "triggers": ["templated proto"],
                        "side_effects": True,
                        "requires_confirmation": True,
                        "steps": [{"type": "say", "text": "Hello {{target}}"}],
                    }
                ),
                encoding="utf-8",
            )
            loaded = loader_mod.load_file_protocols(custom_dir=str(td))
            steps = loaded[0].build_steps(args={"target": "team"}, user_text="templated proto")
            self.assertEqual(steps[0].get("text"), "Hello team")

    def test_engine_executes_custom_protocol(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "demo.json"
            p.write_text(
                json.dumps(
                    {
                        "name": "custom_chain",
                        "triggers": ["run custom chain"],
                        "side_effects": True,
                        "requires_confirmation": True,
                        "steps": [{"type": "protocol", "name": "monday"}],
                    }
                ),
                encoding="utf-8",
            )
            loaded = loader_mod.load_file_protocols(custom_dir=str(td))
            modules = [monday_mod] + loaded
            engine = engine_mod.ProtocolEngine()
            res = engine.run(
                modules,
                name="custom_chain",
                user_text="run custom chain",
                confirm=True,
                dry_run=False,
                args={},
            )
            self.assertTrue(res.get("ok"))
            self.assertEqual(res.get("action"), "shutdown_app")


if __name__ == "__main__":
    unittest.main()
