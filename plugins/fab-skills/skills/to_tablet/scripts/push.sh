#!/usr/bin/env bash
set -euo pipefail

# Galaxy tablet over Tailscale (Termux sshd). Same target as md_to_pdf.
TABLET_HOST="${TABLET_HOST:-u0_a134@100.94.60.70}"
TABLET_PORT="${TABLET_PORT:-8022}"
TABLET_DIR="${TABLET_DIR:-/storage/emulated/0/Documents}"
# Space-separated folder paths under TABLET_DIR (e.g. "allovista Secore/Canine"); empty = TABLET_DIR itself.
TABLET_SUBDIRS="${TABLET_SUBDIRS:-}"
SSH_OPTS=(-p "$TABLET_PORT" -o StrictHostKeyChecking=accept-new)

DEST_DIRS=()
if [ -z "$TABLET_SUBDIRS" ]; then
  DEST_DIRS=("$TABLET_DIR")
else
  for sub in $TABLET_SUBDIRS; do DEST_DIRS+=("$TABLET_DIR/$sub"); done
fi

for dest in "${DEST_DIRS[@]}"; do
  ssh "${SSH_OPTS[@]}" "$TABLET_HOST" "mkdir -p '$dest'"
done

for pdf in "$@"; do
  # Add the creation date + hour (file mtime) unless the name already carries it.
  base="$(basename "${pdf%.pdf}")"
  if [[ ! "$base" =~ _[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}$ ]]; then
    base="${base}_$(date -r "$pdf" +%Y-%m-%d_%H%M)"
  fi
  name="$base.pdf"
  for dest in "${DEST_DIRS[@]}"; do
    scp -P "$TABLET_PORT" -o StrictHostKeyChecking=accept-new "$pdf" "$TABLET_HOST:$dest/$name"
    # Media scan so the file appears in Android's file browser immediately.
    ssh "${SSH_OPTS[@]}" "$TABLET_HOST" \
      "am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d 'file://$dest/$name' >/dev/null"
    echo "sent $dest/$name"
  done
done
