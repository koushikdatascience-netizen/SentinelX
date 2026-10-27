#!/usr/bin/env bash
set -euo pipefail

backup_dir="${SENTINELX_BACKUP_DIR:-/srv/sentinelx/backups}"
container="${SENTINELX_POSTGRES_CONTAINER:-sentinelx-stage-postgres-1}"
database="${SENTINELX_DATABASE:-sentinelx_stage}"
user="${SENTINELX_DATABASE_USER:-sentinelx_stage}"
stamp="$(date -u +%Y%m%dT%H%M%S%N)"
backup="$backup_dir/sentinelx-${stamp}.dump"
retention_days="${SENTINELX_BACKUP_RETENTION_DAYS:-30}"
if [[ ! "$retention_days" =~ ^[1-9][0-9]*$ ]]; then
  echo "backup retention must be a positive number of days" >&2
  exit 2
fi

install -d -m 700 "$backup_dir"
docker inspect "$container" >/dev/null
docker exec "$container" pg_dump -U "$user" -d "$database" -Fc > "$backup"
test -s "$backup"
docker exec -i "$container" pg_restore --list < "$backup" >/dev/null

check_db="sentinelx_restore_check_${stamp:0:24}"
cleanup() {
  docker exec "$container" dropdb --if-exists -U "$user" "$check_db" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker exec "$container" createdb -U "$user" "$check_db"
docker exec -i "$container" pg_restore --no-owner -U "$user" -d "$check_db" < "$backup"
docker exec "$container" psql -U "$user" -d "$check_db" -Atc 'select count(*) from alembic_version' | grep -qx '1'

chmod 600 "$backup"
find "$backup_dir" -maxdepth 1 -type f -name 'sentinelx-*.dump' -mtime "+$retention_days" -delete
printf '%s\n' "$backup"
