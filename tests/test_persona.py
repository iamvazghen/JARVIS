import importlib.util
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


class PersonaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module(Path("Jarvis") / "brain" / "persona.py", "persona_mod")

    def test_language_detection(self):
        self.assertEqual(self.mod.detect_language_code("hello"), "en")
        self.assertEqual(self.mod.detect_language_code("привет"), "ru")
        self.assertEqual(self.mod.detect_language_code("բարև"), "hy")

    def test_tone_detection(self):
        self.assertEqual(self.mod.infer_tone("do this asap"), "decisive")
        self.assertEqual(self.mod.infer_tone("are you sure this is safe"), "cautious")
        self.assertEqual(self.mod.infer_tone("how does this work?"), "explanatory")

    def test_persona_block_shape(self):
        block = self.mod.persona_block("thanks, great job")
        self.assertIn("Turn persona guidance:", block)
        self.assertIn("Tone:", block)
        self.assertIn("Language:", block)


if __name__ == "__main__":
    unittest.main()
