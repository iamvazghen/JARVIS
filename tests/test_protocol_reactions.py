import importlib.util
import types
import sys
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


def _install_stub_dependencies():
    if "Jarvis" not in sys.modules:
        sys.modules["Jarvis"] = types.ModuleType("Jarvis")

    config_pkg = types.ModuleType("Jarvis.config")
    config_mod = types.ModuleType("Jarvis.config.config")
    config_mod.llm_api_key = ""
    config_mod.llm_base_url = ""
    config_mod.llm_model = ""
    config_mod.llm_fast_model = ""
    config_mod.protocol_ai_reactions = "0"
    config_mod.protocol_reaction_ai_judge = "0"
    config_mod.protocol_reaction_timeout_s = 3
    config_mod.protocol_reaction_max_words = 18
    config_pkg.config = config_mod
    sys.modules["Jarvis.config"] = config_pkg
    sys.modules["Jarvis.config.config"] = config_mod

    brain_pkg = types.ModuleType("Jarvis.brain")
    llm_mod = types.ModuleType("Jarvis.brain.llm")

    class _LLMError(Exception):
        pass

    def _chat_completions(**kwargs):
        return ""

    llm_mod.LLMError = _LLMError
    llm_mod.chat_completions = _chat_completions
    sys.modules["Jarvis.brain"] = brain_pkg
    sys.modules["Jarvis.brain.llm"] = llm_mod


_install_stub_dependencies()
reactions_mod = _load_module(Path("Jarvis") / "protocols" / "reactions.py", "protocol_reactions")


class ProtocolReactionsTests(unittest.TestCase):
    def test_detect_language_from_text(self):
        self.assertEqual(reactions_mod.detect_language_from_text("Привет"), "ru")
        self.assertEqual(reactions_mod.detect_language_from_text("Բարև"), "hy")
        self.assertEqual(reactions_mod.detect_language_from_text("Hello"), "en")

    def test_pick_returns_text_for_all_languages(self):
        ru = reactions_mod.pick("protocol_house_party", user_text="запусти протокол")
        hy = reactions_mod.pick("protocol_house_party", user_text="գործարկիր պրոտոկոլ")
        en = reactions_mod.pick("protocol_house_party", user_text="run protocol now")
        self.assertTrue(isinstance(ru, str) and len(ru.strip()) > 0)
        self.assertTrue(isinstance(hy, str) and len(hy.strip()) > 0)
        self.assertTrue(isinstance(en, str) and len(en.strip()) > 0)

    def test_needs_custom_reaction_heuristic(self):
        spec = {
            "side_effects": True,
            "args_schema": {"input_path": {"type": "string", "required": True}},
        }
        self.assertTrue(
            reactions_mod._needs_custom_reaction_heuristic(
                protocol_name="protocol_studio_transcode",
                spec=spec,
                user_text="Please do this carefully, I am not sure this is safe.",
                lang="en",
                tone="cautious",
            )
        )
        self.assertFalse(
            reactions_mod._needs_custom_reaction_heuristic(
                protocol_name="protocol_mark5_boot",
                spec={"side_effects": False, "args_schema": {}},
                user_text="run protocol mark5 boot",
                lang="en",
                tone="supportive",
            )
        )


if __name__ == "__main__":
    unittest.main()
