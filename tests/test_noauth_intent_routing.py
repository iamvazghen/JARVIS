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


class NoAuthIntentRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brain_mod = _load_module(
            Path("Jarvis") / "brain" / "intent_routing.py",
            "brain_intent_routing_mod",
        )

    def test_codeinterpreter_route(self):
        plan = self.brain_mod.required_noauth_mcp_plan("Use code interpreter: print(2+2)")
        self.assertEqual(plan[0], "mcp_execute")
        self.assertEqual(plan[1].get("tool_name"), "AUTO_TOOLKIT:codeinterpreter")

    def test_composio_search_route(self):
        plan = self.brain_mod.required_noauth_mcp_plan("Composio search latest AI agent news")
        self.assertEqual(plan[0], "mcp_execute")
        self.assertEqual(plan[1].get("tool_name"), "AUTO_TOOLKIT:composio_search")

    def test_hackernews_route(self):
        plan = self.brain_mod.required_noauth_mcp_plan("hacker news top stories")
        self.assertEqual(plan[0], "mcp_execute")
        self.assertEqual(plan[1].get("tool_name"), "AUTO_TOOLKIT:hackernews")

    def test_text_to_pdf_route(self):
        plan = self.brain_mod.required_noauth_mcp_plan("text to pdf Meeting notes for tomorrow")
        self.assertEqual(plan[0], "mcp_execute")
        self.assertEqual(plan[1].get("tool_name"), "AUTO_TOOLKIT:text_to_pdf")

    def test_yelp_route(self):
        plan = self.brain_mod.required_noauth_mcp_plan("find sushi places on yelp in san francisco")
        self.assertEqual(plan[0], "mcp_execute")
        self.assertEqual(plan[1].get("tool_name"), "AUTO_TOOLKIT:yelp")

    def test_telegram_send_route(self):
        plan = self.brain_mod.required_telegram_mcp_plan("telegram send hello from jivan")
        self.assertEqual(plan[0], "mcp_execute")
        self.assertEqual(plan[1].get("tool_name"), "TELEGRAM_SEND_MESSAGE")

    def test_telegram_delete_route(self):
        plan = self.brain_mod.required_telegram_mcp_plan("telegram delete")
        self.assertEqual(plan[0], "mcp_execute")
        self.assertEqual(plan[1].get("tool_name"), "TELEGRAM_DELETE_MESSAGE")


if __name__ == "__main__":
    unittest.main()
