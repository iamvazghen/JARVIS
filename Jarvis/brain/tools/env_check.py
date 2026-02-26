import os


def spec():
    return {
        "name": "env_check",
        "description": "Check required environment variables for JIVAN integrations and report what is missing.",
        "args": {},
    }


def run(*, assistant=None, wolfram_fn=None):
    required = [
        "JIVAN_LLM_API_KEY",
        "JIVAN_LLM_BASE_URL",
        "JIVAN_LLM_MODEL",
        "JIVAN_OPENWEATHER_API_KEY",
        "JIVAN_WOLFRAMALPHA_ID",
    ]
    present = [k for k in required if os.getenv(k)]
    missing = [k for k in required if not os.getenv(k)]
    return {"present": present, "missing": missing}
