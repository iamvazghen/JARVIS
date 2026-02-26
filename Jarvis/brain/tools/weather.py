def spec():
    return {
        "name": "weather",
        "description": "Get current weather summary for a city (requires OpenWeatherMap API key).",
        "args": {"city": "string"},
    }


def run(*, assistant, wolfram_fn=None, city=""):
    return assistant.weather(city)

