import re
import urllib.parse
import webbrowser


def _looks_like_url(text):
    t = (text or "").strip().lower()
    return t.startswith("http://") or t.startswith("https://")


def _normalize_target(target):
    target = (target or "").strip()
    if not target:
        return None

    if _looks_like_url(target):
        return target

    # If it's multiple words, treat as a search query
    if re.search(r"\s", target):
        return "https://www.google.com/search?q=" + urllib.parse.quote_plus(target)

    t = target.lower()
    common = {
        "youtube": "youtube.com",
        "google": "google.com",
        "gmail": "mail.google.com",
        "github": "github.com",
        "reddit": "reddit.com",
        "twitter": "x.com",
        "x": "x.com",
        "stackoverflow": "stackoverflow.com",
    }
    if t in common:
        return "https://www." + common[t] if "." in common[t] and not common[t].startswith("mail.") else "https://" + common[t]

    # Add .com if user said "open youtube" / "open google" style single token
    if "." not in target:
        target = target + ".com"

    return "https://www." + target


def website_opener(domain):
    try:
        url = _normalize_target(domain)
        if not url:
            return False
        webbrowser.open_new_tab(url)
        return True
    except Exception as e:
        print(e)
        return False
