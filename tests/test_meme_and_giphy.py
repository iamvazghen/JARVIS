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


class MemeAndGiphyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.intent_mod = _load_module(
            Path("Jarvis") / "brain" / "intent_routing.py",
            "intent_routing_meme_giphy_mod",
        )
        cls.imgflip_mod = _load_module(
            Path("Jarvis") / "brain" / "tools" / "imgflip_meme.py",
            "imgflip_tool_mod",
        )

    def test_giphy_route(self):
        plan = self.intent_mod.required_noauth_mcp_plan("giphy happy coding")
        self.assertEqual(plan[0], "mcp_execute")
        self.assertEqual(plan[1].get("tool_name"), "AUTO_TOOLKIT:giphy")

    def test_imgflip_missing_text(self):
        res = self.imgflip_mod.run(top_text="", bottom_text="")
        self.assertFalse(res.get("ok"))
        self.assertEqual(res.get("error_code"), "missing_text")

    def test_imgflip_get_memes_without_credentials(self):
        class _Resp:
            ok = True

            @staticmethod
            def json():
                return {
                    "success": True,
                    "data": {"memes": [{"id": "1", "name": "X", "url": "https://i.imgflip.com/x.jpg"}]},
                }

        old_get = self.imgflip_mod.requests.get
        self.imgflip_mod.requests.get = lambda *a, **k: _Resp()
        try:
            res = self.imgflip_mod.run(action="get_memes")
            self.assertTrue(res.get("ok"))
            self.assertTrue(isinstance((res.get("data") or {}).get("memes"), list))
        finally:
            self.imgflip_mod.requests.get = old_get

    def test_imgflip_search_requires_credentials(self):
        old_user = os.environ.get("JIVAN_IMGFLIP_USERNAME")
        old_pass = os.environ.get("JIVAN_IMGFLIP_PASSWORD")
        os.environ["JIVAN_IMGFLIP_USERNAME"] = ""
        os.environ["JIVAN_IMGFLIP_PASSWORD"] = ""
        try:
            res = self.imgflip_mod.run(action="search_memes", query="drake")
            self.assertFalse(res.get("ok"))
            self.assertEqual(res.get("error_code"), "missing_credentials")
        finally:
            if old_user is None:
                os.environ.pop("JIVAN_IMGFLIP_USERNAME", None)
            else:
                os.environ["JIVAN_IMGFLIP_USERNAME"] = old_user
            if old_pass is None:
                os.environ.pop("JIVAN_IMGFLIP_PASSWORD", None)
            else:
                os.environ["JIVAN_IMGFLIP_PASSWORD"] = old_pass


if __name__ == "__main__":
    unittest.main()
