# Public 24/7 Deployment (Professional)

## Stack
- `docker-compose.public.yml` services:
  - `jivan` app
  - `redis`
  - `nginx` reverse proxy
  - `tailscale` mesh node
  - `fail2ban`
  - `uptime-kuma`

## 1) Prepare host
- Ubuntu 22.04+ (recommended)
- Install Docker + Compose plugin
- Open ports `80/443` only (plus SSH)

## 2) Configure env
- Place production secrets in server `.env` only.
- Add:
  - `TS_AUTHKEY=<tailscale-auth-key>`
  - `JIVAN_SECURITY_ENFORCE_SOURCE_ALLOWLIST=1`
  - `JIVAN_SECURITY_ALLOWED_SOURCE_IPS=<comma-separated trusted IPs>`
  - `JIVAN_SECURITY_REQUIRE_TAILSCALE_FOR_REMOTE=1`
  - `JIVAN_SECURITY_ALLOWED_TAILSCALE_CIDRS=100.64.0.0/10`
  - `JIVAN_SECURITY_ALLOWED_TELEGRAM_USER_IDS=<your telegram user id>`

## 3) Start services
```bash
cd deploy
docker compose -f docker-compose.public.yml up -d
```

## 4) HTTPS/domain
- Put real `server_name` in `nginx.conf`.
- Use certbot/caddy for TLS certificates.
- Redirect all HTTP to HTTPS.

## 5) Security policy
- With allowlist enabled, remote command execution is denied unless:
  - source IP is allowlisted
  - source IP is inside allowed Tailscale CIDR (if required)
  - Telegram sender is allowlisted (if sender allowlist configured)

## 6) Monitoring
- Access Uptime Kuma on port `3001`.
- Add checks for app process, Redis ping, and audit scripts.

## 7) Rotation
- Rotate all API keys regularly.
- Re-run:
  - `python scripts/audit_tool_usage.py`
  - `python scripts/audit_security.py`
