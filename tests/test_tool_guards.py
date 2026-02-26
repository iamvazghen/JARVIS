import unittest
import importlib.util
from pathlib import Path


def _load_module(relative_path, module_name):
    repo_root = Path(__file__).resolve().parents[1]
    mod_path = repo_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, str(mod_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


google_can_run = _load_module(
    Path("Jarvis") / "brain" / "tools" / "google_search.py",
    "google_search_tool",
).can_run
website_can_run = _load_module(
    Path("Jarvis") / "brain" / "tools" / "open_website.py",
    "open_website_tool",
).can_run


class ToolGuardTests(unittest.TestCase):
    def test_open_website_requires_explicit_navigation_intent(self):
        self.assertTrue(website_can_run(user_text="open github.com", domain="github.com"))
        self.assertTrue(website_can_run(user_text="go to docs.python.org", domain="docs.python.org"))
        self.assertFalse(website_can_run(user_text="what is open source", domain="github.com"))
        self.assertFalse(website_can_run(user_text="open something", domain=""))

    def test_google_search_requires_search_intent_and_query(self):
        self.assertTrue(
            google_can_run(user_text="search google for python decorators", query="python decorators")
        )
        self.assertFalse(google_can_run(user_text="google is useful", query="python decorators"))
        self.assertFalse(google_can_run(user_text="search google for nothing", query=""))

if __name__ == "__main__":
    unittest.main()
