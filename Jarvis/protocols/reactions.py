import random
import re

from Jarvis.config import config
from Jarvis.brain.llm import LLMError, chat_completions


def _normalize_lang(lang):
    t = (lang or "").strip().lower()
    if t.startswith("ru"):
        return "ru"
    if t.startswith("hy"):
        return "hy"
    return "en"


def detect_language_from_text(text):
    s = str(text or "")
    for ch in s:
        code = ord(ch)
        if 0x0530 <= code <= 0x058F:
            return "hy"
        if 0x0400 <= code <= 0x04FF:
            return "ru"
    return "en"


def _protocol_risk(spec):
    s = spec or {}
    steps = s.get("steps") or []
    for step in steps:
        if not isinstance(step, dict):
            continue
        if (step.get("type") or "").strip().lower() == "action":
            name = (step.get("name") or "").strip().lower()
            if name == "shutdown_pc":
                return "critical"
            if name == "shutdown_app":
                return "high"
    if s.get("side_effects"):
        return "high"
    return "normal"


def _reaction_tone(spec):
    risk = _protocol_risk(spec)
    if risk == "critical":
        return "cautious"
    if risk == "high":
        return "assertive"
    return "supportive"


_REACTIONS = {
    "en": {
        "supportive": [
            "Great choice. I am executing the protocol.",
            "Solid decision. Protocol is now starting.",
            "Nice call. Running that protocol for you.",
            "Good move. I will handle it right away.",
            "That works well. Executing now.",
            "Clean decision. Protocol launch in progress.",
        ],
        "assertive": [
            "Understood. Executing the requested protocol now.",
            "Acknowledged. I am running the protocol.",
            "Affirmative. Protocol execution has started.",
            "Copy that. I am proceeding with this protocol.",
            "Command accepted. Protocol in motion.",
            "Request confirmed. Executing now.",
        ],
        "cautious": [
            "High-impact choice noted. Proceeding with protocol execution.",
            "Critical action recognized. Executing with caution.",
            "Understood. This is a serious action, and I am proceeding now.",
            "Decision accepted. Initiating high-impact protocol.",
            "I understand the risk profile. Executing now.",
            "Confirmed. Proceeding carefully with this protocol.",
        ],
    },
    "ru": {
        "supportive": [
            "Отличный выбор. Запускаю протокол.",
            "Хорошее решение. Выполняю протокол.",
            "Принято. Сейчас запущу протокол.",
            "Сильный ход. Выполняю прямо сейчас.",
            "Логично. Перехожу к выполнению.",
            "Понял вас. Запускаю протокол.",
        ],
        "assertive": [
            "Принято. Выполняю указанный протокол.",
            "Подтверждаю. Запуск протокола начат.",
            "Команда получена. Протокол выполняется.",
            "Понял. Приступаю к выполнению.",
            "Есть. Протокол уже в работе.",
            "Запрос зафиксирован. Выполняю.",
        ],
        "cautious": [
            "Понимаю, действие серьезное. Запускаю осторожно.",
            "Риск высокий. Выполняю протокол.",
            "Критичный шаг принят. Приступаю к выполнению.",
            "Подтверждаю решение. Запускаю с осторожностью.",
            "Это важное действие. Выполняю сейчас.",
            "Принято. Выполняю протокол аккуратно.",
        ],
    },
    "hy": {
        "supportive": [
            "Լավ ընտրություն է, սկսում եմ պրոտոկոլը։",
            "Հիանալի որոշում, հիմա կկատարեմ։",
            "Ընդունված է, պրոտոկոլը գործարկվում է։",
            "Ճիշտ քայլ է, անմիջապես անցնում եմ կատարմանը։",
            "Պարզ է, հիմա կաշխատացնեմ պրոտոկոլը։",
            "Համաձայն եմ, սկսում եմ հիմա։",
        ],
        "assertive": [
            "Հասկացա, պրոտոկոլը հիմա կկատարվի։",
            "Հրամանը ընդունված է, սկսում եմ կատարումը։",
            "Ստացվեց, անցնում եմ գործարկման։",
            "Հաստատված է, կատարումը մեկնարկում է։",
            "Ընդունված է, աշխատում եմ դրա վրա։",
            "Լավ, անմիջապես գործարկում եմ։",
        ],
        "cautious": [
            "Սա բարձր ազդեցության որոշում է, բայց անցնում եմ կատարմանը։",
            "Ռիսկային քայլ է, կատարում եմ զգուշությամբ։",
            "Քննադատական գործողություն է, բայց սկսում եմ հիմա։",
            "Հասկացա ռիսկը, գործարկում եմ զգուշորեն։",
            "Սա լուրջ հրաման է, անցնում եմ կատարմանը։",
            "Ընդունված է, պրոտոկոլը կգործարկեմ զգուշությամբ։",
        ],
    },
}


def _pick_static(lang, tone):
    l = _normalize_lang(lang)
    bucket = _REACTIONS.get(l) or _REACTIONS["en"]
    msgs = bucket.get(tone) or bucket.get("assertive") or _REACTIONS["en"]["assertive"]
    return random.choice(list(msgs))


def _ai_enabled():
    flag = str(getattr(config, "protocol_ai_reactions", "1")).strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return False
    api_key = getattr(config, "llm_api_key", "") or ""
    base_url = getattr(config, "llm_base_url", "") or ""
    model = getattr(config, "llm_fast_model", "") or getattr(config, "llm_model", "") or ""
    return bool(api_key and base_url and model)


def _needs_custom_reaction_heuristic(*, protocol_name, spec, user_text, lang, tone):
    text = str(user_text or "").strip().lower()
    if not text:
        return False

    # If request is long/nuanced, a contextual one-liner is usually better than a canned phrase.
    if len(text) >= 120:
        return True

    # High-impact actions benefit from custom caution when user wording suggests uncertainty/risk.
    risk_markers = (
        "danger",
        "risky",
        "are you sure",
        "not sure",
        "hesitate",
        "force",
        "urgent",
        "emergency",
        "careful",
        "double check",
    )
    if any(m in text for m in risk_markers):
        return True

    # If protocol has required args and user provided rich detail, custom preamble is useful.
    args_schema = (spec or {}).get("args_schema") or {}
    has_required_args = any(
        isinstance(rule, dict) and rule.get("required") for rule in args_schema.values()
    )
    if has_required_args and len(text.split()) > 10:
        return True

    # Critical protocols can still use static cautious templates unless context is nuanced.
    if tone == "cautious" and ("because" in text or "if" in text or "unless" in text):
        return True

    return False


def _needs_custom_reaction_ai(*, protocol_name, spec, user_text, lang, tone):
    api_key = getattr(config, "llm_api_key", "") or ""
    base_url = getattr(config, "llm_base_url", "") or ""
    model = getattr(config, "llm_fast_model", "") or getattr(config, "llm_model", "") or ""
    timeout_s = int(getattr(config, "protocol_reaction_timeout_s", 6))
    system = (
        "Decide if a canned protocol reaction is sufficient.\n"
        "Return only YES or NO.\n"
        "YES means: use a custom reaction.\n"
        "NO means: use a standard canned reaction.\n"
    )
    payload = {
        "protocol_name": protocol_name,
        "protocol_description": (spec or {}).get("description", ""),
        "side_effects": bool((spec or {}).get("side_effects")),
        "tone": tone,
        "lang": lang,
        "user_text": user_text,
    }
    try:
        ans = chat_completions(
            api_key=api_key,
            base_url=base_url,
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": str(payload)}],
            timeout_s=max(2, min(timeout_s, 5)),
        )
    except LLMError:
        return False
    out = str(ans or "").strip().upper()
    return out.startswith("YES")


def _needs_custom_reaction(*, protocol_name, spec, user_text, lang, tone):
    if _needs_custom_reaction_heuristic(
        protocol_name=protocol_name,
        spec=spec,
        user_text=user_text,
        lang=lang,
        tone=tone,
    ):
        return True
    if not _ai_enabled():
        return False

    # Optional AI second-opinion switch.
    ai_judge = str(getattr(config, "protocol_reaction_ai_judge", "1")).strip().lower()
    if ai_judge not in ("1", "true", "yes", "on"):
        return False
    return _needs_custom_reaction_ai(
        protocol_name=protocol_name,
        spec=spec,
        user_text=user_text,
        lang=lang,
        tone=tone,
    )


def _build_ai_reaction(*, protocol_name, spec, user_text, lang, tone):
    api_key = getattr(config, "llm_api_key", "") or ""
    base_url = getattr(config, "llm_base_url", "") or ""
    model = getattr(config, "llm_fast_model", "") or getattr(config, "llm_model", "") or ""
    max_words = int(getattr(config, "protocol_reaction_max_words", 18))
    timeout_s = int(getattr(config, "protocol_reaction_timeout_s", 6))

    system = (
        "You generate short spoken reaction lines before protocol execution.\n"
        "Rules:\n"
        f"- Language: {lang}\n"
        f"- Tone: {tone}\n"
        f"- Max words: {max_words}\n"
        "- One sentence only.\n"
        "- No emojis.\n"
        "- Mention confidence/judgment naturally.\n"
        "- Do not include JSON.\n"
    )
    payload = {
        "protocol_name": protocol_name,
        "user_text": user_text,
        "protocol_side_effects": bool((spec or {}).get("side_effects")),
        "protocol_description": (spec or {}).get("description", ""),
    }
    try:
        text = chat_completions(
            api_key=api_key,
            base_url=base_url,
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": str(payload)}],
            timeout_s=timeout_s,
        )
    except LLMError:
        return ""

    out = str(text or "").strip()
    out = re.sub(r"\s+", " ", out)
    if not out:
        return ""
    words = out.split(" ")
    if len(words) > max_words:
        out = " ".join(words[:max_words]).strip()
    return out


def pick(protocol_name, *, user_text="", spec=None, lang=""):
    lang = _normalize_lang(lang or detect_language_from_text(user_text))
    tone = _reaction_tone(spec or {})
    need_custom = _needs_custom_reaction(
        protocol_name=(protocol_name or "").strip().lower(),
        spec=(spec or {}),
        user_text=user_text,
        lang=lang,
        tone=tone,
    )
    if need_custom and _ai_enabled():
        ai = _build_ai_reaction(
            protocol_name=(protocol_name or "").strip().lower(),
            spec=(spec or {}),
            user_text=user_text,
            lang=lang,
            tone=tone,
        )
        if ai:
            return ai
    return _pick_static(lang, tone)
