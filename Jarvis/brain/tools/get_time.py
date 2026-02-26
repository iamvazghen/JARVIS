def spec():
    return {
        "name": "get_time",
        "description": "Get the current time as a short string.",
        "args": {},
    }


def run(*, assistant, wolfram_fn=None):
    return assistant.tell_time()

