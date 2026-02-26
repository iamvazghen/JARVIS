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


def _install_stub_config(
    *,
    enabled="1",
    api_key="",
    allowlist="",
    use_tool_router="0",
    tool_router_url="",
    tool_router_session_id="",
    auto_create_session="1",
    external_user_id="",
    enable_noauth_toolkits="0",
    noauth_toolkits="",
    giphy_auth_config_id="",
    telegram_auth_config_id="",
    gmail_auth_config_id="",
):
    if "Jarvis" not in sys.modules:
        sys.modules["Jarvis"] = types.ModuleType("Jarvis")
    config_pkg = types.ModuleType("Jarvis.config")
    config_mod = types.ModuleType("Jarvis.config.config")
    config_mod.composio_mcp_enabled = enabled
    config_mod.composio_api_key = api_key
    config_mod.composio_base_url = ""
    config_mod.composio_entity_id = "default"
    config_mod.composio_tool_allowlist = allowlist
    config_mod.composio_use_tool_router = use_tool_router
    config_mod.composio_tool_router_url = tool_router_url
    config_mod.composio_tool_router_session_id = tool_router_session_id
    config_mod.composio_auto_create_session = auto_create_session
    config_mod.composio_external_user_id = external_user_id
    config_mod.composio_enable_noauth_toolkits = enable_noauth_toolkits
    config_mod.composio_noauth_toolkits = noauth_toolkits
    config_mod.composio_giphy_auth_config_id = giphy_auth_config_id
    config_mod.composio_telegram_auth_config_id = telegram_auth_config_id
    config_mod.composio_gmail_auth_config_id = gmail_auth_config_id
    config_pkg.config = config_mod
    sys.modules["Jarvis.config"] = config_pkg
    sys.modules["Jarvis.config.config"] = config_mod


def _install_stub_composio():
    composio_mod = types.ModuleType("composio")

    class ComposioToolSet:
        instances = []

        def __init__(self, api_key="", base_url=""):
            self.api_key = api_key
            self.base_url = base_url
            self.calls = []
            ComposioToolSet.instances.append(self)

        def get_tools(self):
            return [{"name": "GMAIL_SEND_EMAIL"}, {"name": "GOOGLECALENDAR_CREATE_EVENT"}]

        def execute_tool(self, tool_name="", arguments=None):
            self.calls.append({"tool_name": tool_name, "arguments": arguments or {}})
            return {"status": "ok", "tool_name": tool_name}

    composio_mod.ComposioToolSet = ComposioToolSet

    class _Session:
        def __init__(self, mcp):
            self.mcp = mcp

    class Composio:
        instances = []

        def __init__(self, api_key=""):
            self.api_key = api_key
            self.create_calls = []
            self.tools_get_calls = []
            parent = self

            class _Tools:
                def get(self, *args, **kwargs):
                    parent.tools_get_calls.append({"args": args, "kwargs": kwargs})
                    return [{"name": "CODEINTERPRETER_EXECUTE_CODE"}]

            self.tools = _Tools()
            Composio.instances.append(self)

        def create(self, user_id=""):
            self.create_calls.append({"user_id": user_id})
            return _Session("https://backend.composio.dev/tool_router/trs_auto123/mcp")

    composio_mod.Composio = Composio
    sys.modules["composio"] = composio_mod
    return ComposioToolSet, Composio


class ComposioMCPTests(unittest.TestCase):
    def test_health_disabled(self):
        _install_stub_config(enabled="0", api_key="")
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_a")
        client = mod.ComposioMCPClient()
        health = client.health_check(force=True)
        self.assertFalse(health.get("enabled"))
        self.assertEqual(health.get("status"), "disabled")

    def test_health_missing_api_key(self):
        _install_stub_config(enabled="1", api_key="")
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_b")
        client = mod.ComposioMCPClient()
        health = client.health_check(force=True)
        self.assertTrue(health.get("enabled"))
        self.assertFalse(health.get("ok"))
        self.assertEqual(health.get("status"), "missing_api_key")

    def test_list_and_execute_with_stub_sdk(self):
        _install_stub_config(enabled="1", api_key="cp_test")
        ToolSet, _ = _install_stub_composio()
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_c")
        client = mod.ComposioMCPClient()

        listed = client.list_tools()
        self.assertTrue(listed.get("ok"))
        self.assertIn("GMAIL_SEND_EMAIL", listed.get("tools", []))

        executed = client.execute(tool_name="GMAIL_SEND_EMAIL", tool_input={"to": "user@example.com"})
        self.assertTrue(executed.get("ok"))
        self.assertEqual(executed.get("tool_name"), "GMAIL_SEND_EMAIL")
        self.assertTrue(len(ToolSet.instances[-1].calls) >= 1)

        health = client.health_check(force=True)
        self.assertTrue(health.get("ok"))
        self.assertEqual(health.get("status"), "connected")

    def test_allowlist_blocks_tool(self):
        _install_stub_config(enabled="1", api_key="cp_test", allowlist="GMAIL_SEND_EMAIL")
        _install_stub_composio()
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_d")
        client = mod.ComposioMCPClient()
        blocked = client.execute(tool_name="GOOGLECALENDAR_CREATE_EVENT", tool_input={})
        self.assertFalse(blocked.get("ok"))
        self.assertEqual(blocked.get("error_code"), "tool_not_allowed")

    def test_mcp_tools_bridge_to_client(self):
        if "Jarvis" not in sys.modules:
            sys.modules["Jarvis"] = types.ModuleType("Jarvis")
        brain_pkg = types.ModuleType("Jarvis.brain")
        mcp_pkg = types.ModuleType("Jarvis.brain.mcp")

        class FakeClient:
            def list_tools(self):
                return {"ok": True, "tools": ["A", "B"]}

            def execute(self, *, tool_name, tool_input=None):
                return {"ok": True, "tool_name": tool_name, "data": tool_input or {}}

        mcp_pkg.ComposioMCPClient = FakeClient
        sys.modules["Jarvis.brain"] = brain_pkg
        sys.modules["Jarvis.brain.mcp"] = mcp_pkg

        list_mod = _load_module(Path("Jarvis") / "brain" / "tools" / "mcp_list_tools.py", "mcp_tool_list_mod")
        exec_mod = _load_module(Path("Jarvis") / "brain" / "tools" / "mcp_execute.py", "mcp_tool_exec_mod")

        listed = list_mod.run()
        executed = exec_mod.run(tool_name="A", tool_input={"x": 1})
        self.assertTrue(listed.get("ok"))
        self.assertEqual(listed.get("tools"), ["A", "B"])
        self.assertTrue(executed.get("ok"))
        self.assertEqual(executed.get("tool_name"), "A")

    def test_tool_router_jsonrpc_flow(self):
        _install_stub_config(
            enabled="1",
            api_key="cp_test",
            use_tool_router="1",
            tool_router_url="https://backend.composio.dev/tool_router/test/mcp",
            tool_router_session_id="test",
        )
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_e")

        calls = []

        class DummyResp:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        def fake_post(url, headers=None, json=None, timeout=0):
            calls.append({"url": url, "headers": headers or {}, "json": json or {}, "timeout": timeout})
            method = (json or {}).get("method")
            if method == "initialize":
                return DummyResp({"jsonrpc": "2.0", "id": (json or {}).get("id"), "result": {"serverInfo": {}}})
            if method == "tools/list":
                return DummyResp(
                    {
                        "jsonrpc": "2.0",
                        "id": (json or {}).get("id"),
                        "result": {"tools": [{"name": "GMAIL_SEND_EMAIL"}]},
                    }
                )
            if method == "tools/call":
                return DummyResp(
                    {
                        "jsonrpc": "2.0",
                        "id": (json or {}).get("id"),
                        "result": {"content": [{"type": "text", "text": "ok"}]},
                    }
                )
            return DummyResp({"jsonrpc": "2.0", "id": (json or {}).get("id"), "error": {"message": "bad method"}})

        mod.requests.post = fake_post
        client = mod.ComposioMCPClient()
        listed = client.list_tools()
        self.assertTrue(listed.get("ok"))
        self.assertEqual(listed.get("tools"), ["GMAIL_SEND_EMAIL"])
        executed = client.execute(tool_name="GMAIL_SEND_EMAIL", tool_input={"to": "a@example.com"})
        self.assertTrue(executed.get("ok"))
        self.assertEqual(executed.get("tool_name"), "GMAIL_SEND_EMAIL")
        methods = [c.get("json", {}).get("method") for c in calls]
        self.assertTrue("initialize" in methods)
        self.assertTrue("tools/list" in methods)
        self.assertTrue("tools/call" in methods)

    def test_tool_router_auto_create_session_when_url_missing(self):
        _install_stub_config(
            enabled="1",
            api_key="cp_test",
            use_tool_router="1",
            tool_router_url="",
            auto_create_session="1",
            external_user_id="pg-test-pg-test-abc",
        )
        _toolset, Composio = _install_stub_composio()
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_f")

        client = mod.ComposioMCPClient()
        status = client._ensure_tool_router_session()
        self.assertTrue(status.get("ok"))
        self.assertTrue(client.tool_router_url.endswith("/mcp"))
        self.assertTrue(len(Composio.instances) >= 1)
        self.assertTrue(len(Composio.instances[-1].create_calls) >= 1)

    def test_list_tools_includes_noauth_toolkits(self):
        _install_stub_config(
            enabled="1",
            api_key="cp_test",
            use_tool_router="1",
            tool_router_url="https://backend.composio.dev/tool_router/test/mcp",
            enable_noauth_toolkits="1",
            noauth_toolkits="codeinterpreter,composio_search",
            external_user_id="pg-test-user",
        )
        _toolset, Composio = _install_stub_composio()
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_g")

        class DummyResp:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        def fake_post(url, headers=None, json=None, timeout=0):
            method = (json or {}).get("method")
            if method == "initialize":
                return DummyResp({"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {}}})
            if method == "tools/list":
                return DummyResp({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "GMAIL_SEND_EMAIL"}]}})
            return DummyResp({"jsonrpc": "2.0", "id": 3, "error": {"message": "bad method"}})

        mod.requests.post = fake_post
        client = mod.ComposioMCPClient()
        listed = client.list_tools()
        self.assertTrue(listed.get("ok"))
        tools = listed.get("tools", [])
        self.assertTrue("GMAIL_SEND_EMAIL" in tools)
        self.assertTrue("CODEINTERPRETER_EXECUTE_CODE" in tools)
        self.assertTrue(len(Composio.instances) >= 1)
        self.assertTrue(len(Composio.instances[-1].tools_get_calls) >= 1)

    def test_auto_toolkit_name_resolution(self):
        _install_stub_config(
            enabled="1",
            api_key="cp_test",
            use_tool_router="1",
            tool_router_url="https://backend.composio.dev/tool_router/test/mcp",
            enable_noauth_toolkits="0",
        )
        _install_stub_composio()
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_h")

        class DummyResp:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        def fake_post(url, headers=None, json=None, timeout=0):
            method = (json or {}).get("method")
            if method == "initialize":
                return DummyResp({"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {}}})
            if method == "tools/list":
                return DummyResp(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "result": {"tools": [{"name": "CODEINTERPRETER_EXECUTE_CODE"}]},
                    }
                )
            if method == "tools/call":
                return DummyResp({"jsonrpc": "2.0", "id": 3, "result": {"ok": True}})
            return DummyResp({"jsonrpc": "2.0", "id": 4, "error": {"message": "bad method"}})

        mod.requests.post = fake_post
        client = mod.ComposioMCPClient()
        res = client.execute(
            tool_name="AUTO_TOOLKIT:codeinterpreter",
            tool_input={"code": "print(1)", "_action_hint": "EXECUTE"},
        )
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("tool_name"), "CODEINTERPRETER_EXECUTE_CODE")

    def test_giphy_default_auth_config_applies(self):
        _install_stub_config(
            enabled="1",
            api_key="cp_test",
            giphy_auth_config_id="ac_test_giphy",
        )
        ToolSet, _ = _install_stub_composio()
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_i")
        client = mod.ComposioMCPClient()
        executed = client.execute(tool_name="GIPHY_SEARCH_GIFS", tool_input={"q": "hello"})
        self.assertTrue(executed.get("ok"))
        last_call = ToolSet.instances[-1].calls[-1]
        self.assertEqual(last_call.get("tool_name"), "GIPHY_SEARCH_GIFS")
        self.assertEqual(last_call.get("arguments", {}).get("auth_config_id"), "ac_test_giphy")

    def test_telegram_default_auth_config_applies(self):
        _install_stub_config(
            enabled="1",
            api_key="cp_test",
            telegram_auth_config_id="ac_test_telegram",
        )
        ToolSet, _ = _install_stub_composio()
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_j")
        client = mod.ComposioMCPClient()
        executed = client.execute(tool_name="TELEGRAM_GET_ME", tool_input={})
        self.assertTrue(executed.get("ok"))
        last_call = ToolSet.instances[-1].calls[-1]
        self.assertEqual(last_call.get("tool_name"), "TELEGRAM_GET_ME")
        self.assertEqual(last_call.get("arguments", {}).get("auth_config_id"), "ac_test_telegram")

    def test_gmail_default_auth_config_applies(self):
        _install_stub_config(
            enabled="1",
            api_key="cp_test",
            gmail_auth_config_id="ac_test_gmail",
        )
        ToolSet, _ = _install_stub_composio()
        mod = _load_module(Path("Jarvis") / "brain" / "mcp" / "composio_client.py", "composio_mod_k")
        client = mod.ComposioMCPClient()
        executed = client.execute(tool_name="GMAIL_GET_PROFILE", tool_input={})
        self.assertTrue(executed.get("ok"))
        last_call = ToolSet.instances[-1].calls[-1]
        self.assertEqual(last_call.get("tool_name"), "GMAIL_GET_PROFILE")
        self.assertEqual(last_call.get("arguments", {}).get("auth_config_id"), "ac_test_gmail")


if __name__ == "__main__":
    unittest.main()
