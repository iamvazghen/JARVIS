from Jarvis.config import config
from Jarvis.brain.llm import LLMError, chat_completions


def spec():
    return {
        "name": "translate_text",
        "description": "Translate text to a target language using the configured LLM.",
        "args": {"text": "string", "target_language": "string"},
    }


def run(*, assistant=None, wolfram_fn=None, text="", target_language="English"):
    text = (text or "").strip()
    if not text:
        return ""

    api_key = getattr(config, "llm_api_key", "")
    base_url = getattr(config, "llm_base_url", "")
    model = getattr(config, "llm_model", "")
    if not (api_key and base_url and model):
        return {"ok": False, "error_code": "missing_llm_config"}

    lang = (target_language or "English").strip()
    try:
        translated = chat_completions(
            api_key=api_key,
            base_url=base_url,
            model=model,
            messages=[
                {"role": "system", "content": "You are JIVAN. Translate accurately."},
                {"role": "user", "content": f"Translate to {lang}:\n\n{text}"},
            ],
            timeout_s=30,
        )
        return {"ok": True, "translated": translated, "target_language": lang}
    except LLMError:
        return {"ok": False, "error_code": "llm_failed"}
