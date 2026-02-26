def spec():
    return {
        "name": "system_info",
        "description": "Get CPU/RAM (and battery if available) system status string.",
        "args": {},
    }


def run(*, assistant, wolfram_fn=None):
    return assistant.system_info()

