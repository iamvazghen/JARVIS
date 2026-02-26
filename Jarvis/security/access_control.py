import ipaddress

from Jarvis.config import config


def _as_bool(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _csv(value):
    return [x.strip() for x in str(value or "").split(",") if x.strip()]


def _ip_in_cidrs(ip_str, cidrs):
    if not ip_str:
        return False
    try:
        ip_obj = ipaddress.ip_address(str(ip_str).strip())
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if ip_obj in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def is_telegram_identity_allowed(user_id=None, username=None):
    allowed_ids = set(_csv(getattr(config, "security_allowed_telegram_user_ids", "")))
    allowed_names = {x.lower().lstrip("@") for x in _csv(getattr(config, "security_allowed_telegram_usernames", ""))}
    if not allowed_ids and not allowed_names:
        return True
    if user_id is not None and str(user_id) in allowed_ids:
        return True
    if username and str(username).lower().lstrip("@") in allowed_names:
        return True
    return False


def validate_source_access(source_context):
    """
    source_context example:
      {
        "source": "telegram|http|local",
        "ip": "100.100.10.12",
        "telegram_user_id": 123,
        "telegram_username": "myuser"
      }
    """
    ctx = source_context if isinstance(source_context, dict) else {}
    if not _as_bool(getattr(config, "security_enforce_source_allowlist", "0")):
        return True, ""

    source = str(ctx.get("source", "local")).strip().lower()
    ip = str(ctx.get("ip", "")).strip()
    if source == "telegram":
        if not is_telegram_identity_allowed(
            user_id=ctx.get("telegram_user_id"),
            username=ctx.get("telegram_username"),
        ):
            return False, "telegram_identity_not_allowlisted"
        return True, ""

    allowed_ips = _csv(getattr(config, "security_allowed_source_ips", "127.0.0.1,::1"))
    if ip and ip in allowed_ips:
        ip_ok = True
    else:
        ip_ok = False

    remote = source not in ("local", "desktop_mic")
    if remote and _as_bool(getattr(config, "security_require_tailscale_for_remote", "1")):
        tailscale_cidrs = _csv(getattr(config, "security_allowed_tailscale_cidrs", "100.64.0.0/10"))
        if not _ip_in_cidrs(ip, tailscale_cidrs):
            return False, "remote_source_not_in_tailscale_range"

    if remote and not ip_ok:
        return False, "source_ip_not_allowlisted"

    return True, ""
