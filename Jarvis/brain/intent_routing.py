import re


def _extract_after_keyword(text, keyword):
    src = str(text or "")
    lower_src = src.lower()
    idx = lower_src.find(keyword.lower())
    if idx == -1:
        return ""
    return src[idx + len(keyword) :].strip(" :,-")


def _extract_weather_city(user_text):
    lowered = (user_text or "").strip().lower()
    m = re.search(r"\bweather(?:\s+in)?\s+(.+)$", lowered)
    if not m:
        return ""
    return m.group(1).strip()


def required_noauth_mcp_plan(user_text):
    text = (user_text or "").strip()
    lowered = text.lower()
    if not lowered:
        return None

    if "code interpreter" in lowered or "codeinterpreter" in lowered:
        code = (
            _extract_after_keyword(text, "code interpreter")
            or _extract_after_keyword(text, "codeinterpreter")
            or text
        )
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:codeinterpreter",
                "tool_input": {"code": code, "_action_hint": "EXECUTE"},
            },
        )

    if "composio search" in lowered:
        query = _extract_after_keyword(text, "composio search") or text
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:composio_search",
                "tool_input": {"query": query, "_action_hint": "SEARCH"},
            },
        )

    if "browser tool" in lowered or "use browser tool" in lowered:
        target = _extract_after_keyword(text, "browser tool") or text
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:browser_tool",
                "tool_input": {"query": target, "_action_hint": "BROWSER"},
            },
        )

    if "hacker news" in lowered or re.search(r"\bhn\b", lowered):
        query = _extract_after_keyword(text, "hacker news") or "top stories"
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:hackernews",
                "tool_input": {"query": query, "_action_hint": "TOP"},
            },
        )

    if "openweathermap" in lowered or "weathermap" in lowered:
        city = _extract_weather_city(text) or _extract_after_keyword(text, "openweathermap")
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:weathermap",
                "tool_input": {"city": city or text, "_action_hint": "WEATHER"},
            },
        )

    if "text to pdf" in lowered:
        body = _extract_after_keyword(text, "text to pdf") or text
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:text_to_pdf",
                "tool_input": {"text": body, "filename": "jivan_output.pdf", "_action_hint": "PDF"},
            },
        )

    if "entelligence" in lowered:
        prompt = _extract_after_keyword(text, "entelligence") or text
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:entelligence",
                "tool_input": {"prompt": prompt, "_action_hint": "ANALYZE"},
            },
        )

    if "use gemini" in lowered or "with gemini" in lowered or lowered.startswith("gemini "):
        prompt = (
            _extract_after_keyword(text, "use gemini")
            or _extract_after_keyword(text, "with gemini")
            or _extract_after_keyword(text, "gemini")
            or text
        )
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:gemini",
                "tool_input": {"prompt": prompt, "_action_hint": "GENERATE"},
            },
        )

    if "on yelp" in lowered or "use yelp" in lowered or lowered.startswith("yelp "):
        query = (
            _extract_after_keyword(text, "on yelp")
            or _extract_after_keyword(text, "use yelp")
            or _extract_after_keyword(text, "yelp")
            or text
        )
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:yelp",
                "tool_input": {"query": query, "_action_hint": "SEARCH"},
            },
        )

    if "seat geek" in lowered or "seatgeek" in lowered:
        query = _extract_after_keyword(text, "seat geek") or _extract_after_keyword(text, "seatgeek") or text
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:seat_geek",
                "tool_input": {"query": query, "_action_hint": "EVENT"},
            },
        )

    if "giphy" in lowered or "gif" in lowered:
        query = (
            _extract_after_keyword(text, "giphy")
            or _extract_after_keyword(text, "gif")
            or text
        )
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:giphy",
                "tool_input": {"query": query, "_action_hint": "SEARCH"},
            },
        )

    if lowered.startswith("composio "):
        prompt = _extract_after_keyword(text, "composio") or text
        return (
            "mcp_execute",
            {
                "tool_name": "AUTO_TOOLKIT:composio",
                "tool_input": {"prompt": prompt, "_action_hint": "RUN"},
            },
        )
    return None


def _split_first_token(text):
    value = str(text or "").strip()
    if not value:
        return "", ""
    parts = value.split(None, 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1].strip()


def _assistant_requested_telegram_message(recent_messages):
    if not isinstance(recent_messages, list):
        return False
    for row in reversed(recent_messages[-8:]):
        if not isinstance(row, dict):
            continue
        if str(row.get("role", "")).lower() != "assistant":
            continue
        text = str(row.get("content", "")).lower()
        if "telegram" in text and (
            "what would you like the message to say" in text
            or "what would you like me to send" in text
            or "what message should i send" in text
            or "need two details" in text
        ):
            return True
    return False


def required_telegram_mcp_plan(user_text, recent_messages=None):
    text = (user_text or "").strip()
    lowered = text.lower()
    if not lowered:
        return None

    if lowered.startswith("telegram send "):
        body = _extract_after_keyword(text, "telegram send")
        if body:
            return ("mcp_execute", {"tool_name": "TELEGRAM_SEND_MESSAGE", "tool_input": {"text": body}})

    # Fuzzy speech recognition variants for "telegram" (e.g., "telly").
    if "send" in lowered and (" telegram" in f" {lowered}" or " telly" in f" {lowered}"):
        msg = _extract_after_keyword(text, "send")
        msg = re.sub(r"\b(to\s+)?(telegram|telly)\b", "", msg, flags=re.IGNORECASE).strip(" :,-")
        if msg:
            return ("mcp_execute", {"tool_name": "TELEGRAM_SEND_MESSAGE", "tool_input": {"text": msg}})

    # Natural-language variants: "send <message> to telegram", "send to telegram <message>".
    m = re.search(r"^\s*send\s+(.+?)\s+to\s+telegram\s*$", lowered, re.IGNORECASE)
    if m:
        body = text[m.start(1) : m.end(1)].strip()
        if body:
            return ("mcp_execute", {"tool_name": "TELEGRAM_SEND_MESSAGE", "tool_input": {"text": body}})
    if lowered.startswith("send to telegram "):
        body = _extract_after_keyword(text, "send to telegram")
        if body:
            return ("mcp_execute", {"tool_name": "TELEGRAM_SEND_MESSAGE", "tool_input": {"text": body}})

    if lowered.startswith("telegram reply "):
        body = _extract_after_keyword(text, "telegram reply")
        if body:
            return (
                "mcp_execute",
                {
                    "tool_name": "TELEGRAM_SEND_MESSAGE",
                    "tool_input": {"text": body, "_reply_to_last": True},
                },
            )

    if lowered.startswith("telegram poll "):
        body = _extract_after_keyword(text, "telegram poll")
        if body:
            segments = [x.strip() for x in body.split("|") if x.strip()]
            if len(segments) >= 3:
                question = segments[0]
                options = segments[1:]
                return (
                    "mcp_execute",
                    {
                        "tool_name": "TELEGRAM_SEND_POLL",
                        "tool_input": {"question": question, "options": options},
                    },
                )

    if lowered.startswith("telegram photo "):
        body = _extract_after_keyword(text, "telegram photo")
        target, caption = _split_first_token(body)
        if target:
            return (
                "mcp_execute",
                {
                    "tool_name": "TELEGRAM_SEND_PHOTO",
                    "tool_input": {"photo": target, "caption": caption},
                },
            )

    if lowered.startswith("telegram document "):
        body = _extract_after_keyword(text, "telegram document")
        target, caption = _split_first_token(body)
        if target:
            return (
                "mcp_execute",
                {
                    "tool_name": "TELEGRAM_SEND_DOCUMENT",
                    "tool_input": {"document": target, "caption": caption},
                },
            )

    if lowered.startswith("telegram edit "):
        body = _extract_after_keyword(text, "telegram edit")
        if "::" in body:
            raw_id, new_text = body.split("::", 1)
            raw_id = raw_id.strip()
            new_text = new_text.strip()
        else:
            raw_id = ""
            new_text = body.strip()
        if new_text:
            tool_input = {"text": new_text, "_use_last_message_id": True}
            if raw_id.isdigit():
                tool_input["message_id"] = int(raw_id)
            return ("mcp_execute", {"tool_name": "TELEGRAM_EDIT_MESSAGE", "tool_input": tool_input})

    if lowered.startswith("telegram delete"):
        body = _extract_after_keyword(text, "telegram delete")
        tool_input = {"_use_last_message_id": True}
        if body.isdigit():
            tool_input["message_id"] = int(body)
        return ("mcp_execute", {"tool_name": "TELEGRAM_DELETE_MESSAGE", "tool_input": tool_input})

    if lowered.startswith("telegram updates"):
        return ("mcp_execute", {"tool_name": "TELEGRAM_GET_UPDATES", "tool_input": {"limit": 20}})

    # Continuation turn: after assistant asked "what should I send to telegram",
    # treat short "say ..." answers as Telegram message content.
    if _assistant_requested_telegram_message(recent_messages):
        if lowered.startswith("just say "):
            body = _extract_after_keyword(text, "just say")
            if body:
                return ("mcp_execute", {"tool_name": "TELEGRAM_SEND_MESSAGE", "tool_input": {"text": body}})
        if lowered.startswith("say "):
            body = _extract_after_keyword(text, "say")
            if body:
                return ("mcp_execute", {"tool_name": "TELEGRAM_SEND_MESSAGE", "tool_input": {"text": body}})

    return None
