from Jarvis.brain.mcp import ComposioMCPClient


def spec():
    return {
        "name": "mcp_execute",
        "description": "Execute one Composio MCP tool with a structured input object.",
        "args": {"tool_name": "string", "tool_input": "object"},
        "required": ["tool_name"],
        "side_effects": True,
    }


def can_run(*, user_text, tool_name="", tool_input=None):
    t = (user_text or "").lower()
    if "mcp" in t or "composio" in t:
        return True
    return bool(str(tool_name or "").strip())


def run(*, assistant=None, wolfram_fn=None, tool_name="", tool_input=None):
    client = ComposioMCPClient()
    return client.execute(tool_name=tool_name, tool_input=tool_input)
