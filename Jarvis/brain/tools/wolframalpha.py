def spec():
    return {
        "name": "wolframalpha",
        "description": "Compute/answer factual queries via WolframAlpha (best for math).",
        "args": {"query": "string"},
    }


def run(*, assistant, wolfram_fn, query=""):
    return wolfram_fn(query)

