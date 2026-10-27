#!/usr/bin/env bash
set -euo pipefail

root="${SENTINELX_ROOT:-/srv/sentinelx}"
sha="${1:-}"
incoming="$root/releases/.incoming-${sha}.tar"
release_dir="$root/releases/$sha"
env_file="$root/source/.env.sentinelx"
compose="$release_dir/deploy/hostinger/compose.yml"

if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  echo "deployment requires a full 40-character commit SHA" >&2
  exit 2
fi
test -f "$incoming"
test -f "$env_file"
test "$(stat -c '%a' "$env_file")" = "600"
test -f "$compose"
python3 "$release_dir/deploy/hostinger/configure-runtime.py" "$env_file" "$release_dir/.sentinelx-meta-key"

current_file="$root/current-release"
previous="legacy"
if [[ -s "$current_file" ]]; then
  previous="$(cat "$current_file")"
fi
if [[ ! "$previous" =~ ^(legacy|[0-9a-f]{40})$ ]]; then
  echo "stored previous release is invalid; refusing automatic deployment" >&2
  exit 1
fi

bash "$release_dir/deploy/hostinger/backup.sh"
env SENTINELX_RELEASE="$sha" docker compose -p sentinelx-stage --env-file "$env_file" -f "$compose" build backend frontend

rollback_previous() {
  echo "restoring previous SentinelX application services: $previous" >&2
  if [[ "$previous" == legacy ]]; then
    env SENTINELX_RELEASE=legacy docker compose -p sentinelx-stage --env-file "$env_file" -f "$root/source/deploy/oracle-staging.compose.yml" up -d --no-deps --no-build --wait --wait-timeout 180 backend frontend
  else
    env SENTINELX_RELEASE="$previous" docker compose -p sentinelx-stage --env-file "$env_file" -f "$root/releases/$previous/deploy/hostinger/compose.yml" up -d --no-deps --no-build --wait --wait-timeout 180 backend frontend
  fi
}

if ! env SENTINELX_RELEASE="$sha" docker compose -p sentinelx-stage --env-file "$env_file" -f "$compose" up -d --no-deps --wait --wait-timeout 240 backend frontend; then
  echo "new release failed container health checks; database schema was left at its forward migration level" >&2
  rollback_previous || echo "application rollback also failed; investigate SentinelX container logs" >&2
  exit 1
fi

if ! SENTINELX_FRONTEND_URL=http://127.0.0.1:13000 SENTINELX_HEALTH_URL=http://127.0.0.1:18080 bash "$release_dir/deploy/hostinger/healthcheck.sh" "$sha" ||
   ! SENTINELX_BASE_URL=https://sentinelx.kamalwoodcraft.in bash "$release_dir/deploy/hostinger/healthcheck.sh" "$sha"; then
  echo "local or public release verification failed; rolling back application services only" >&2
  rollback_previous || echo "application rollback also failed; investigate SentinelX container logs" >&2
  exit 1
fi

printf '%s\n' "$sha" > "$current_file.tmp"
chmod 600 "$current_file.tmp"
mv -f "$current_file.tmp" "$current_file"
ln -sfn "$release_dir" "$root/releases/current"
install -o root -g root -m 755 "$release_dir/deploy/hostinger/backup.sh" /usr/local/sbin/sentinelx-backup
printf '%s\n' "Deployed release $sha. The verified database backup is retained under $root/backups."
