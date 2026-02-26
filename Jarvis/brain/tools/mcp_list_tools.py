from Jarvis.brain.mcp import ComposioMCPClient


def spec():
    return {
        "name": "mcp_list_tools",
        "description": "List available Composio MCP tools accessible to JIVAN.",
        "args": {},
    }


def run(*, assistant=None, wolfram_fn=None):
    client = ComposioMCPClient()
    return client.list_tools()
