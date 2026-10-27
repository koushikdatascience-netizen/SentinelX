#!/usr/bin/env bash
set -euo pipefail

root="${SENTINELX_ROOT:-/srv/sentinelx}"
release="${1:-}"
env_file="$root/source/.env.sentinelx"

if [[ ! "$release" =~ ^(legacy|[0-9a-f]{40})$ ]]; then
  echo "usage: bash rollback.sh <legacy|40-character-commit-sha>" >&2
  exit 2
fi

if [[ "$release" == legacy ]]; then
  compose="$root/source/deploy/oracle-staging.compose.yml"
  env SENTINELX_RELEASE=legacy docker compose -p sentinelx-stage --env-file "$env_file" -f "$compose" up -d --no-deps --no-build --wait --wait-timeout 180 backend frontend
  check_script="$root/releases/current/deploy/hostinger/healthcheck.sh"
  bash "$check_script" ""
  printf '%s\n' legacy > "$root/current-release.tmp"
  ln -sfn "$root/source" "$root/releases/current"
else
  compose="$root/releases/$release/deploy/hostinger/compose.yml"
  test -f "$compose"
  env SENTINELX_RELEASE="$release" docker compose -p sentinelx-stage --env-file "$env_file" -f "$compose" up -d --no-deps --no-build --wait --wait-timeout 180 backend frontend
  bash "$root/releases/$release/deploy/hostinger/healthcheck.sh" "$release"
  printf '%s\n' "$release" > "$root/current-release.tmp"
  ln -sfn "$root/releases/$release" "$root/releases/current"
fi

chmod 600 "$root/current-release.tmp"
mv -f "$root/current-release.tmp" "$root/current-release"
printf '%s\n' "Rolled application services back to $release; database schema was not rolled back."
