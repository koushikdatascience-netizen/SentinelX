#!/usr/bin/env bash
set -euo pipefail

request="${SSH_ORIGINAL_COMMAND:-}"
if [[ ! "$request" =~ ^receive[[:space:]]([0-9a-f]{40})$ ]]; then
  echo "only receive <full-commit-sha> is permitted" >&2
  exit 2
fi
sha="${BASH_REMATCH[1]}"
incoming="/srv/sentinelx/incoming/.incoming-${sha}.tar"

umask 077
cat > "$incoming"
size="$(stat -c '%s' "$incoming")"
if [[ "$size" -lt 1 || "$size" -gt 100000000 ]]; then
  rm -f "$incoming"
  echo "source archive size is outside the permitted range" >&2
  exit 1
fi
sudo -n /usr/local/sbin/sentinelx-deploy "$sha" "$incoming"
