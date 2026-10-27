#!/usr/bin/env bash
set -euo pipefail

root="/srv/sentinelx"
sha="${1:-}"
user_archive="${2:-}"
if [[ ! "$sha" =~ ^[0-9a-f]{40}$ || "$user_archive" != "$root/incoming/.incoming-$sha.tar" ]]; then
  echo "invalid release or archive path" >&2
  exit 2
fi

root_archive="$root/releases/.incoming-$sha.tar"
release_dir="$root/releases/$sha"
trap 'rm -f "$root_archive" "$user_archive"' EXIT
install -o root -g root -m 600 "$user_archive" "$root_archive"

if tar -tf "$root_archive" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
  echo "archive contains an unsafe path" >&2
  exit 1
fi
test "$(tar -xOf "$root_archive" .sentinelx-release)" = "$sha"
install -d -o root -g root -m 700 "$release_dir"
tar -xf "$root_archive" -C "$release_dir" --no-same-owner --no-same-permissions
test -f "$release_dir/deploy/hostinger/compose.yml"

SENTINELX_ROOT="$root" bash "$release_dir/deploy/hostinger/deploy.sh" "$sha"
