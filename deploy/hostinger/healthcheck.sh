#!/usr/bin/env bash
set -euo pipefail

base_url="${SENTINELX_BASE_URL:-https://sentinelx.kamalwoodcraft.in}"
expected_release="${1:-}"

headers_file="$(mktemp)"
body_file="$(mktemp)"
trap 'rm -f "$headers_file" "$body_file"' EXIT

curl --fail --silent --show-error --max-time 20 -D "$headers_file" -o /dev/null "$base_url/"
curl --fail --silent --show-error --max-time 20 -D "$headers_file" -o "$body_file" "$base_url/health"
python3 - "$body_file" "$expected_release" <<'PY'
import json
import pathlib
import sys

body = json.loads(pathlib.Path(sys.argv[1]).read_text())
if body.get("status") != "ok":
    raise SystemExit("backend health status was not ok")
if sys.argv[2] and body.get("release") != sys.argv[2]:
    raise SystemExit("backend release did not match requested release")
print(f"backend health ok; mode={body.get('mode')}; release={body.get('release')}")
PY

curl --fail --silent --show-error --max-time 20 -o /dev/null "$base_url/demo"
printf '%s\n' "frontend root and /demo returned HTTP 200; backend health verified"
