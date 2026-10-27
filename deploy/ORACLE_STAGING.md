# Historical Oracle staging plan (not the current deployment target)

SentinelX is currently staged on Hostinger. Use [docs/HOSTINGER_DEPLOYMENT.md](../docs/HOSTINGER_DEPLOYMENT.md) for the audited host, current release, and deployment procedure. This file is retained for historical reference and rollback compatibility; do not provision or deploy to Oracle based on this guide.

Use a **separate** Docker Compose project and a **new** Nginx server block; do not modify Kamal Woodcraft's application, database, containers or existing Nginx vhost.

## Confirm the VM before deploying
Run on the Oracle VM:

```bash
uname -m
free -h
df -h /
docker --version && docker compose version
sudo nginx -t
sudo ss -lntup | grep -E ':80|:443|:13000|:18080'
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

`aarch64` means ARM64; the Docker images in this stack support Linux ARM64. Ensure the website has backups, free disk (prefer 5 GB or more), and at least 1.5 GB spare RAM. On a 1 GB AMD Micro free VM, do **not** run this three-container stack; move to a separate ARM A1 instance or smaller deployment.

## DNS
In the authoritative DNS provider for `kamalwoodcraft.in`, create just one new A record:
`sentinelx.kamalwoodcraft.in -> <Oracle server public IPv4>`.
Do not change the root domain, www, or existing Kamal Woodcraft records.

## Deploy after verifying VM resources

Fresh backend containers run Alembic before starting. If this database already exists from a `create_all` deployment, back it up and review schema adoption in `docs/EVIDENCE_DRAFT_MILESTONE.md` before running the updated image. Do not blindly stamp revisions. No existing database has been migrated by this change.
```bash
git clone https://github.com/koushikdatascience-netizen/SentinelX.git sentinelx
cd sentinelx
cp deploy/.env.sentinelx.example .env.sentinelx
# Edit .env.sentinelx with unique strong secrets, chmod 600
# Set SENTINELX_REGISTRATION_ALLOWED_EMAILS to approved test emails only.
# Empty means no signup; existing accounts can still sign in.
docker compose --env-file .env.sentinelx -f deploy/oracle-staging.compose.yml config
docker compose --env-file .env.sentinelx -f deploy/oracle-staging.compose.yml up -d --build
curl -fsS http://127.0.0.1:18080/health
curl -I http://127.0.0.1:13000/
```
Always run the new Compose file only. It maps frontend to loopback port 13000 and API to loopback port 18080.

## Reverse proxy and TLS
1. Copy the separate `deploy/nginx-sentinelx.conf.example` into a **new** /etc/nginx/sites-available/sentinelx.conf file; do not edit Kamal Woodcraft's config.
2. Link it from sites-enabled, run `sudo nginx -t` first and reload only if valid.
3. Obtain TLS with Certbot for `sentinelx.kamalwoodcraft.in` after DNS resolves; verify certificate and HTTPS behavior.

## Before sharing the public URL
Owner-scoped persistent approvals and an operator-managed registration email allowlist are implemented. Email ownership is not verified. **Not production ready:** add sign-in rate limiting, stronger account lifecycle controls, secure public research egress, session policy, DB migration strategy, backups, and provider usage accounting. `ENABLE_LEGACY_ENDPOINTS=false`, `INFERENCE_PROVIDER=demo`, `ALLOW_PAID_INFERENCE=false`, and `META_APP_BUDGET_CENTS=0` remain enabled for staging.

Kamal Woodcraft remains unchanged. A broken SentinelX demo should not be able to access the existing site's secrets or its database. Monitor memory and disk; apply service resource limits, verify no port conflict and take backups before any infrastructure change.

**No host deployment or DNS change has been executed from GitHub.** Server access/size/IP are not available through this chat. This is a ready-to-review staging plan, not a deployed public URL.
