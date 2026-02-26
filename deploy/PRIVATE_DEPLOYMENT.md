# Private Deployment Runbook (Single Owner Access)

## 1) Host hardening (Windows or Linux)
- Enable full-disk encryption.
- Create a non-admin runtime user for JIVAN.
- Keep OS auto-updates enabled.

## 2) Network boundary
- Use Tailscale for private operator access.
- Do not expose JIVAN UI/API to public internet.
- If dashboard is needed remotely, publish only through Cloudflare Zero Trust with identity policy.

## 3) Services
- Start private infra:
  - `docker compose -f deploy/docker-compose.private.yml up -d`
- Redis will bind to localhost only.
- Uptime Kuma will bind to localhost only.

## 4) App runtime
- Configure `.env`:
  - `JIVAN_REDIS_ENABLED=1`
  - `JIVAN_REDIS_URL=redis://localhost:6379/0`
- Run JIVAN in service mode:
  - Windows: NSSM service wrapper
  - Linux: systemd user service

## 5) Access control
- Keep API keys only in `.env` on the host.
- Rotate leaked/previously shared keys.
- Restrict Telegram bot command handling to your user ID.

## 6) Monitoring and recovery
- Use Uptime Kuma probes for:
  - JIVAN process alive
  - Redis ping
  - Composio MCP health endpoint checks (through local script)
- Keep daily backup for:
  - `memories_local.jsonl`
  - `telegram_state.json`
  - Redis AOF volume

## 7) Security checks before go-live
- Run:
  - `python scripts/audit_tool_usage.py`
  - `python scripts/audit_security.py`
- Fix any `status=fail` result before production.
