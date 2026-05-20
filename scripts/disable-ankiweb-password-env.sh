#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${HEADLESS_ANKI_ENV_FILE:-$HOME/.config/headless-anki/ankiweb.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi

umask 077
tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT
awk -F= '
  BEGIN {
    saw_login=0; saw_sync=0; saw_conflict=0
  }
  $1 == "HEADLESS_ANKIWEB_PASSWORD" { next }
  $1 == "HEADLESS_ANKIWEB_LOGIN" { print "HEADLESS_ANKIWEB_LOGIN=0"; saw_login=1; next }
  $1 == "HEADLESS_ANKIWEB_SYNC_ON_START" { print "HEADLESS_ANKIWEB_SYNC_ON_START=1"; saw_sync=1; next }
  $1 == "HEADLESS_ANKIWEB_CONFLICT_ACTION" { print; saw_conflict=1; next }
  { print }
  END {
    if (!saw_login) print "HEADLESS_ANKIWEB_LOGIN=0"
    if (!saw_sync) print "HEADLESS_ANKIWEB_SYNC_ON_START=1"
    if (!saw_conflict) print "HEADLESS_ANKIWEB_CONFLICT_ACTION=cancel"
  }
' "$ENV_FILE" > "$tmp_file"
mv "$tmp_file" "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "Removed HEADLESS_ANKIWEB_PASSWORD and disabled startup login. Stored sync auth in the Anki profile will be used on future starts."
