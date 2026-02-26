def spec():
    return {
        "name": "my_location",
        "description": "Get your approximate city/state/country based on IP geolocation.",
        "args": {},
    }


def run(*, assistant, wolfram_fn=None):
    city, state, country = assistant.my_location()
    return {"city": city, "state": state, "country": country}

