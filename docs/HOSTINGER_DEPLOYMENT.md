# SentinelX on Hostinger

## Current audited deployment

Audited on 28 October 2026. The public URL is [https://sentinelx.kamalwoodcraft.in](https://sentinelx.kamalwoodcraft.in).

- Host: Hostinger VPS `srv2008681`, Ubuntu 24.04, x86_64. Docker 29.8.1 and Compose 5.5.1; 31 GiB memory, 387 GiB root disk.
- Runtime: isolated Docker Compose project `sentinelx-stage`.
- Source checkout: `/srv/sentinelx/source`.
- Active checkout SHA: `665afd30188605370c6a017b479e9cda35313f38` (`codex/indie-demo-readiness`).
- Current `origin/main`: `a931a0d0bb1a55e783be1ad5c7116f08522aad8c`. Its successful Backend checks run is [40571398910](https://github.com/koushikdatascience-netizen/SentinelX/actions/runs/40571398910). The active Hostinger checkout is not that main commit.
- Backend: Compose service/container `backend` / `sentinelx-stage-backend-1`, port 8000 in the container and loopback-only host port 18080.
- Frontend: service/container `frontend` / `sentinelx-stage-frontend-1`, port 3000 in the container and loopback-only host port 13000.
- Database: `postgres:16-alpine`, service/container `postgres` / `sentinelx-stage-postgres-1`, private Compose port 5432. Its persistent volume is `sentinelx-stage_sentinelx_pg`; current Alembic revision is `0002`.
- Reverse proxy: Caddy container `livekit-caddy`, host configuration `/etc/caddy/Caddyfile`. The SentinelX site sends `/api/*` and `/health` to `127.0.0.1:18080`, and all other paths to `127.0.0.1:13000`. Caddy provisions TLS. Nginx is not the active proxy.
- Environment file: `/srv/sentinelx/source/.env.sentinelx`, mode 0600. This guide and deployment scripts never print its contents.
- The application runs in demo mode; public registration is disabled and paid inference and live multimodal are off. Public `/api/v1/status` labels unverified text, vision, and image outputs as `sample`; unsupported segmentation and transcription are not advertised as live. `META_VERIFIED_CAPABILITIES` is unset by default and should only be populated after a corresponding successful, authorized manual live smoke call.

At audit time, the homepage and `/demo` returned HTTP 200; `/health` returned HTTP 200; `/api/v1/meta/readiness` returned 401 as expected without authentication. Seven Next.js static assets loaded with HTTP 200. The newly prepared `/api/v1/status` endpoint is not on the currently running image yet. The site is a staging application and has not been promoted to a production service.

The server has no SentinelX-specific deployment timer or webhook. Its active Compose file is currently `/srv/sentinelx/source/deploy/oracle-staging.compose.yml`; that historical filename does not mean the target is Oracle. Existing non-SentinelX containers, Caddy, the main Kamal Woodcraft site, and their configuration are outside SentinelX deployment scope.

## CI and release flow

`.github/workflows/ci.yml` runs backend tests, fresh PostgreSQL migrations, PostgreSQL-backed backend tests, Python dependency consistency, npm advisory audit, frontend production build, and Chromium E2E on pushes to `main` and pull requests.

`.github/workflows/deploy-hostinger.yml` waits for a successful `Backend checks` workflow on a `main` push. It checks out that exact tested SHA, transfers a Git archive over a pinned SSH host key, and invokes a forced-command-only deploy account. It is inert until the repository variable `HOSTINGER_DEPLOY_ENABLED` is set to `true`. Protect the `hostinger-production` GitHub Environment with a reviewer before enabling deployment.

The remote deploy script saves the source under `/srv/sentinelx/releases/<full-sha>`, verifies a PostgreSQL custom-format backup by listing and restoring it to a temporary isolated database, then builds the backend and frontend images tagged with the full SHA. It only updates the `backend` and `frontend` services in Compose project `sentinelx-stage`. It does not run `down`, rebuild or restart Postgres, touch Docker volumes, or modify Caddy. App health checks verify the database connection, release SHA, frontend and public HTTPS routes. A failed app health check restores only the previous application containers. Forward database migrations are not reversed automatically.

### GitHub setup

1. Create a fresh Ed25519 key pair for this deploy connection. Keep its private half outside the repository and add it as the `HOSTINGER_SSH_KEY` secret in GitHub Environment `hostinger-production`.
2. Run `bash deploy/hostinger/install-deploy-user.sh < deploy-key.pub` as root on the VPS from a reviewed checkout of this repository. This installs the `sentinelx-deploy` account with a forced command, no port/agent/X11 forwarding, no PTY, and a narrowly scoped root-owned deployment wrapper. The account can only submit a SHA-labelled source archive; it cannot run an arbitrary shell.
3. Add these remaining Environment secrets:
   - `HOSTINGER_HOST`: `200.97.169.48`
   - `HOSTINGER_USER`: `sentinelx-deploy`
   - `HOSTINGER_KNOWN_HOSTS`: the verified SSH host-key line for this host (verify its fingerprint through Hostinger before saving).
4. Configure the `hostinger-production` Environment with required reviewers. Add repository variable `HOSTINGER_DEPLOY_ENABLED=true` only after the first reviewed deploy is ready.
5. Configure branch protection so `Backend checks` must pass before changes reach `main`. Confirm this protection in GitHub; it is not controlled by the workflow file.

Do not reuse the existing root SSH private key as a GitHub secret. Do not store the Meta API key in GitHub repository files or frontend secrets. The deploy workflow keeps Meta calls disabled.

### Backups

The backup directory is `/srv/sentinelx/backups`. Before this audit, it contained `before-campaign-665afd3.dump` (12 KiB) and host configuration snapshots. The new `backup.sh` produced `sentinelx-20261027T201132592100837.dump` (11,757 bytes; SHA-256 `d3642057de309f972ece416a462ccfbf011df934762d24a808cbbecf644be834`). Its archive listing and a complete restore into a temporary database succeeded; the restored Alembic marker was `0002`, and the temporary database was removed. The deployment installer adds a daily 02:30 UTC systemd backup timer once it is run on the host. Before every release, `backup.sh` writes a mode-0600 custom-format dump, checks its archive table, restores it into a temporary database, confirms the migration marker, and removes that temporary database. Daily backups older than 30 days are pruned only when named `sentinelx-*.dump`; the pre-existing snapshots are not matched.

Manual backup:

```bash
sudo /usr/local/sbin/sentinelx-backup
sudo systemctl status sentinelx-backup.timer --no-pager
```

To check a stored dump without restoring it, use the running SentinelX Postgres container:

```bash
sudo docker exec -i sentinelx-stage-postgres-1 pg_restore --list < /srv/sentinelx/backups/<backup-file>.dump
```

A full restore test is performed by the backup script in a temporary database. It does not overwrite the live database.

### Health checks and release identification

```bash
curl -fsSI https://sentinelx.kamalwoodcraft.in/
curl -fsS https://sentinelx.kamalwoodcraft.in/health
curl -fsSI https://sentinelx.kamalwoodcraft.in/demo
sudo docker compose -p sentinelx-stage -f /srv/sentinelx/releases/current/deploy/hostinger/compose.yml ps
```

`/health` reports database connectivity and `SENTINELX_RELEASE`. The older currently running image predates that release field; the audited source SHA above identifies it until a new release updates the health response.

### Manual deployment

Prefer the CI workflow. For an authorized emergency release, first create and verify a database backup. Use a reviewed full commit SHA from `main`; do not deploy a feature branch directly.

```bash
# From a reviewed checkout; the installer requires the public key on stdin.
bash deploy/hostinger/install-deploy-user.sh < deploy-key.pub

# The normal release route is the CI workflow; its remote forced command receives the archive.
# To restore application containers manually:
sudo SENTINELX_ROOT=/srv/sentinelx bash /srv/sentinelx/releases/current/deploy/hostinger/rollback.sh <legacy-or-full-sha>
```

To confirm whether GitHub deployed a commit, inspect the successful `Deploy Hostinger production` Actions run, read `/srv/sentinelx/current-release` on the host, and compare it with `https://sentinelx.kamalwoodcraft.in/health` `release`. The app health value must match the intended full SHA.

### Troubleshooting

- Check only SentinelX services: `docker compose -p sentinelx-stage -f /srv/sentinelx/releases/current/deploy/hostinger/compose.yml ps`.
- View bounded logs: `docker compose -p sentinelx-stage -f /srv/sentinelx/releases/current/deploy/hostinger/compose.yml logs --tail=100 backend frontend`.
- For the initial release, the rollback target `legacy` uses the existing source checkout's Oracle-named Compose file with the same SentinelX project, database volume and ports. The historical file is retained for rollback and compatibility.
- Never run `docker compose down` for other projects, Docker prune commands, volume deletion, global Caddy/Nginx edits, or a database restore over the live database as part of routine deployment.
- If a migration is incompatible, keep the verified backup, roll back only the app if possible, and require an explicit database recovery review.

## Verification record and limits

- Latest main SHA and successful CI run: verified through the GitHub API from the VPS.
- Active host SHA, Compose labels, Docker containers, private ports, volume name, DB migration, Caddy route, resource capacity, and backup filenames: verified over SSH.
- Public HTTPS homepage, demo, health, and auth-gated readiness routes: checked on 28 October 2026.
- Hostinger CD: configuration prepared in this repository but not active until merged to `main`, deploy account installed, GitHub Environment secrets/variable configured, and its first successful workflow run completes.
- Unrelated Hostinger services: all 8 containers recorded before SentinelX deployment retained the same container IDs and start times during this audit; `kamalwoodcraft.in` and `connect.snapkeystudio.com/api/health` returned HTTP 200.
- A new release, post-release browser journey, daily timer installation, and successful Hostinger CD run remain pending until the restricted deploy account and GitHub Environment are configured.
