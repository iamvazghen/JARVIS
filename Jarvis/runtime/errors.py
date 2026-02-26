_MAP = {
    "missing_api_key": "Integration API key is missing.",
    "connect_failed": "Connection to service failed.",
    "tool_not_allowed": "This tool is currently not allowed by policy.",
    "missing_required_args": "I need more details to run this action.",
    "execution_failed": "The requested action failed while executing.",
    "source_access_denied": "Request blocked by access policy.",
}


def humanize(error_code, details=""):
    code = str(error_code or "").strip()
    msg = _MAP.get(code, "An unexpected error occurred.")
    if details:
        return f"{msg} ({details})"
    return msg

