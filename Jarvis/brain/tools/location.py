def spec():
    return {
        "name": "location",
        "description": "Open Google Maps for a place and compute distance from your current location (side effect).",
        "args": {"place": "string"},
        "side_effects": True,
    }


def can_run(*, user_text, place=""):
    t = (user_text or "").lower()
    return ("where is" in t) or ("location" in t) or ("maps" in t)


def run(*, assistant, wolfram_fn=None, place=""):
    place = (place or "").strip()
    if not place:
        return False
    current_loc, target_loc, distance = assistant.location(place)
    if not current_loc or not target_loc or not distance:
        return False
    city = target_loc.get("city", "")
    state = target_loc.get("state", "")
    country = target_loc.get("country", "")
    if city:
        return f"{place} is in {state} state and country {country}. It is {distance} km away from your current location"
    return f"{place} is in {state} in {country}. It is {distance} km away from your current location"

