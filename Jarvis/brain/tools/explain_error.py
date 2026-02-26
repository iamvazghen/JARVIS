from Jarvis.config import config
from Jarvis.brain.llm import LLMError, chat_completions


def spec():
    return {
        "name": "explain_error",
        "description": "Explain an error/stack trace and suggest fixes using the configured LLM.",
        "args": {"error_text": "string"},
    }


def run(*, assistant=None, wolfram_fn=None, error_text=""):
    error_text = (error_text or "").strip()
    if not error_text:
        return ""

    api_key = getattr(config, "llm_api_key", "")
    base_url = getattr(config, "llm_base_url", "")
    model = getattr(config, "llm_model", "")
    if not (api_key and base_url and model):
        return {"ok": False, "error_code": "missing_llm_config"}

    try:
        explanation = chat_completions(
            api_key=api_key,
            base_url=base_url,
            model=model,
            messages=[
                {"role": "system", "content": "You are JIVAN. Be practical and concise."},
                {"role": "user", "content": "Explain this error and give step-by-step fixes:\n\n" + error_text},
            ],
            timeout_s=30,
        )
        return {"ok": True, "explanation": explanation}
    except LLMError:
        return {"ok": False, "error_code": "llm_failed"}
