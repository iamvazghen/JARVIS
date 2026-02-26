import requests

_SESSION = requests.Session()

class LLMError(Exception):
    pass


def list_models(*, api_key, base_url, timeout_s=30):
    if not api_key:
        raise LLMError("Missing LLM API key.")
    if not base_url:
        raise LLMError("Missing LLM base URL.")

    url = base_url.rstrip("/") + "/models"
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }

    try:
        res = _SESSION.get(url, headers=headers, timeout=timeout_s)
        if not res.ok:
            raise LLMError(f"{res.status_code} {res.text}")
        data = res.json()
    except requests.RequestException as e:
        raise LLMError(str(e))

    try:
        return [m["id"] for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]
    except Exception:
        raise LLMError("Unexpected models response format.")


def chat_completions(*, api_key, base_url, model, messages, timeout_s=30):
    if not api_key:
        raise LLMError("Missing LLM API key.")
    if not base_url:
        raise LLMError("Missing LLM base URL.")
    if not model:
        raise LLMError("Missing LLM model.")

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        res = _SESSION.post(url, headers=headers, json=payload, timeout=timeout_s)
        if not res.ok:
            raise LLMError(f"{res.status_code} {res.text}")
        data = res.json()
    except requests.RequestException as e:
        raise LLMError(str(e))

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise LLMError("Unexpected LLM response format.")
