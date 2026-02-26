from Jarvis.config import config
from Jarvis.brain.llm import LLMError, chat_completions

from .clipboard_get import run as clipboard_get


def spec():
    return {
        "name": "llm_clipboard_summarize",
        "description": "Summarize the current clipboard text using the configured LLM.",
        "args": {"style": "string"},
    }


def run(*, assistant=None, wolfram_fn=None, style="bullet"):
    text = clipboard_get()
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error_code": "empty_clipboard"}

    api_key = getattr(config, "llm_api_key", "")
    base_url = getattr(config, "llm_base_url", "")
    model = getattr(config, "llm_model", "")
    if not (api_key and base_url and model):
        return {"ok": False, "error_code": "missing_llm_config"}

    style = (style or "bullet").strip().lower()
    instruction = (
        "Summarize the following text."
        if style == "paragraph"
        else "Summarize the following text as short bullet points."
    )

    try:
        summary = chat_completions(
            api_key=api_key,
            base_url=base_url,
            model=model,
            messages=[
                {"role": "system", "content": "You are JIVAN. Be concise."},
                {"role": "user", "content": instruction + "\n\nTEXT:\n" + text},
            ],
            timeout_s=30,
        )
        return {"ok": True, "summary": summary}
    except LLMError:
        return {"ok": False, "error_code": "llm_failed"}
