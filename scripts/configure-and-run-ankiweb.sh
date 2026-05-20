#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${HEADLESS_ANKI_ENV_FILE:-$HOME/.config/headless-anki/ankiweb.env}"
EXPORT_DIR="${HEADLESS_ANKI_EXPORT_DIR:-$PROJECT_DIR/runtime/export}"
IMAGE="${HEADLESS_ANKI_IMAGE:-bcbernardo/headless-anki:headless-sync}"
CONTAINER="${HEADLESS_ANKI_CONTAINER:-headless-anki}"
VOLUME="${HEADLESS_ANKI_VOLUME:-headless-anki-data}"

mkdir -p "$(dirname "$ENV_FILE")" "$EXPORT_DIR"
chmod 700 "$(dirname "$ENV_FILE")"

printf 'AnkiWeb username/email: '
IFS= read -r username
printf 'AnkiWeb password (input hidden): '
stty_orig="$(stty -g)"
stty -echo
IFS= read -r password
stty "$stty_orig"
printf '\n'

if [[ -z "$username" || -z "$password" ]]; then
  echo 'Username and password are required.' >&2
  exit 1
fi

umask 077
tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT
{
  printf 'HEADLESS_ANKIWEB_LOGIN=1\n'
  printf 'HEADLESS_ANKIWEB_SYNC_ON_START=1\n'
  printf 'HEADLESS_ANKIWEB_CONFLICT_ACTION=cancel\n'
  printf 'HEADLESS_ANKIWEB_USERNAME=%s\n' "$username"
  printf 'HEADLESS_ANKIWEB_PASSWORD=%s\n' "$password"
} > "$tmp_file"
mv "$tmp_file" "$ENV_FILE"
chmod 600 "$ENV_FILE"

docker volume inspect "$VOLUME" >/dev/null 2>&1 || docker volume create "$VOLUME" >/dev/null
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER" \
  --restart unless-stopped \
  --env-file "$ENV_FILE" \
  -p 127.0.0.1:8765:8765 \
  -v "$VOLUME:/data" \
  -v "$EXPORT_DIR:/export" \
  "$IMAGE"

echo "Started $CONTAINER. AnkiConnect is bound to 127.0.0.1:8765."
