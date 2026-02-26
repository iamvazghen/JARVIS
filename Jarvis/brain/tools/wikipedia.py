def spec():
    return {
        "name": "wikipedia",
        "description": "Get a brief Wikipedia summary for a topic.",
        "args": {"topic": "string"},
    }


def run(*, assistant, wolfram_fn=None, topic=""):
    return assistant.tell_me(topic)

