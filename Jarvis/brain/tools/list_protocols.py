import json

from Jarvis.protocols import list_protocols


def spec():
    return {
        "name": "list_protocols",
        "description": "List all available protocols (executable command bundles).",
        "args": {},
    }


def run(*, assistant=None, wolfram_fn=None):
    return json.loads(json.dumps(list_protocols()))

