#!/usr/bin/env bash
set -euo pipefail

# Converts each Markdown file to <name>.pdf next to the source. Sending to the tablet is the
# to_tablet skill's job (scripts/push.sh there).
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ $# -gt 0 ] || { echo "usage: convert.sh <file.md> [...]" >&2; exit 2; }

# Activate the `science` env, creating it on first run. Discovers conda at runtime,
# so there are no machine-specific paths here.
# shellcheck disable=SC1091
source "$SKILL_DIR/../../scripts/ensure_env.sh"

for md in "$@"; do
  out="${md%.md}.pdf"
  src="$(python "$SKILL_DIR/scripts/render_mermaid.py" "$md")"
  pandoc "$src" -o "$out" --pdf-engine=weasyprint -s \
    --template="$SKILL_DIR/assets/template.html" \
    --css="$SKILL_DIR/assets/secore.css"
  [ "$src" != "$md" ] && rm -f "$src"
  echo "wrote $out"
done
