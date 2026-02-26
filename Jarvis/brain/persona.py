import re


def detect_language_code(text):
    s = str(text or "")
    for ch in s:
        code = ord(ch)
        if 0x0530 <= code <= 0x058F:
            return "hy"
        if 0x0400 <= code <= 0x04FF:
            return "ru"
    return "en"


def infer_tone(user_text, tool_result=None):
    text = str(user_text or "").strip().lower()
    if not text:
        return "neutral"

    urgent_markers = ("urgent", "asap", "right now", "immediately", "now")
    if any(m in text for m in urgent_markers):
        return "decisive"

    cautious_markers = ("danger", "risky", "careful", "are you sure", "double check", "confirm")
    if any(m in text for m in cautious_markers):
        return "cautious"

    positive_markers = ("great", "awesome", "nice", "perfect", "thanks", "thank you")
    if any(m in text for m in positive_markers):
        return "warm"

    if text.endswith("?") or text.startswith(("how", "why", "what", "can you", "could you")):
        return "explanatory"

    tr = tool_result if isinstance(tool_result, dict) else {}
    if tr.get("ok") is False:
        return "supportive"
    return "neutral"


def turn_persona_rules(user_text, tool_result=None):
    lang = detect_language_code(user_text)
    tone = infer_tone(user_text, tool_result=tool_result)
    rules = {
        "lang": lang,
        "tone": tone,
        "max_sentences": 2,
        "style": "concise, clear, action-first",
    }
    if tone == "explanatory":
        rules["max_sentences"] = 3
    if tone == "decisive":
        rules["style"] = "direct, efficient, no filler"
    if tone == "cautious":
        rules["style"] = "risk-aware, explicit tradeoffs"
    if tone == "warm":
        rules["style"] = "professional with light warmth"
    if tone == "supportive":
        rules["style"] = "calm recovery guidance"
    return rules


def persona_block(user_text, tool_result=None):
    rules = turn_persona_rules(user_text, tool_result=tool_result)
    return (
        "Turn persona guidance:\n"
        f"- Language: {rules['lang']}\n"
        f"- Tone: {rules['tone']}\n"
        f"- Style: {rules['style']}\n"
        f"- Max sentences: {rules['max_sentences']}\n"
        "- Be context-aware and consistent with SOUL.md."
    )

