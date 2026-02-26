import os
import re


SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bm0-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
]


def _iter_text_files(repo_root):
    for root, _dirs, files in os.walk(repo_root):
        if ".git" in root:
            continue
        for name in files:
            if name.endswith((".py", ".md", ".json", ".yml", ".yaml", ".txt", ".env", ".example")):
                yield os.path.join(root, name)


def generate_security_report(repo_root):
    findings = []
    for path in _iter_text_files(repo_root):
        rel = os.path.relpath(path, repo_root)
        if rel == ".env":
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        for pat in SECRET_PATTERNS:
            m = pat.search(text)
            if m:
                findings.append(
                    {
                        "file": rel.replace("\\", "/"),
                        "pattern": pat.pattern,
                        "sample": m.group(0)[:12] + "...",
                    }
                )

    # Baseline config hygiene checks.
    env_example = os.path.join(repo_root, ".env.example")
    env_hygiene = {"has_env_example": os.path.exists(env_example), "hardcoded_secrets_in_repo": len(findings)}
    status = "pass" if env_hygiene["has_env_example"] and not findings else "fail"
    return {"status": status, "findings": findings, "env_hygiene": env_hygiene}
