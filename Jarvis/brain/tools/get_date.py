def spec():
    return {
        "name": "get_date",
        "description": "Get today's date as a short string.",
        "args": {},
    }


def run(*, assistant, wolfram_fn=None):
    return assistant.tell_me_date()

