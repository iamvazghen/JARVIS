import re


APP_SUFFIXES = (" app", " application", " program")
GOODBYE_TOKENS = ("goodbye", "offline", "bye")


def normalize_command(text):
    return (text or "").strip().lower()


def extract_after_prefix(command, prefixes):
    raw = (command or "").strip()
    lowered = raw.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return raw[len(prefix) :].strip()
    return ""


def extract_topic(command):
    return extract_after_prefix(command, ("tell me about ", "who is ", "what is "))


def extract_open_target(command):
    return extract_after_prefix(command, ("open ",))


def extract_launch_target(command):
    return extract_after_prefix(command, ("launch ", "start "))


def split_open_target(target):
    t = normalize_command(target)
    for suffix in APP_SUFFIXES:
        if t.endswith(suffix):
            return t[: -len(suffix)].strip(), True
    return t, False


def extract_weather_city(command):
    raw = (command or "").strip()
    lowered = raw.lower()
    m = re.search(r"\bweather(?:\s+in)?\s+(.+)$", lowered)
    if not m:
        return ""
    return m.group(1).strip()


def extract_youtube_query(command):
    lowered = normalize_command(command)
    if "youtube" not in lowered:
        return ""
    cleaned = re.sub(r"\bon youtube\b", "", lowered)
    cleaned = cleaned.replace("youtube", "")
    cleaned = re.sub(r"^(play|search)\s+", "", cleaned)
    return cleaned.strip()


def extract_where_place(command):
    raw = (command or "").strip()
    lowered = raw.lower()
    idx = lowered.find("where is ")
    if idx == -1:
        return ""
    return raw[idx + len("where is ") :].strip()


def is_goodbye(command):
    lowered = normalize_command(command)
    return any(token in lowered for token in GOODBYE_TOKENS)


def wants_monday_protocol(command):
    lowered = normalize_command(command)
    if lowered == "monday":
        return True
    if "monday" not in lowered or "protocol" not in lowered:
        return False
    return any(word in lowered for word in ("run", "launch", "execute"))
