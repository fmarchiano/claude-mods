#!/usr/bin/env bash
set -euo pipefail

# Converts each Markdown file to <name>.pdf next to the source. Sending to the tablet is the
# to_tablet skill's job (scripts/push.sh there).
# Style: cv (default, Fabio's CV look) or secore (SeCore monochrome house style);
# each is assets/<style>.html (pandoc template) + assets/<style>.css.
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
usage() { echo "usage: convert.sh [--style cv|secore] <file.md> [...]" >&2; exit 2; }

style=cv
if [ "${1:-}" = "--style" ]; then style="${2:-}"; shift 2 || usage; fi
[ -f "$SKILL_DIR/assets/$style.css" ] && [ -f "$SKILL_DIR/assets/$style.html" ] || {
  echo "convert.sh: unknown style '$style' (have: cv, secore)" >&2; exit 2; }
[ $# -gt 0 ] || usage

# Activate the `science` env, creating it on first run. Discovers conda at runtime,
# so there are no machine-specific paths here.
# shellcheck disable=SC1091
source "$SKILL_DIR/../../scripts/ensure_env.sh"

for md in "$@"; do
  out="${md%.md}.pdf"
  src="$(python "$SKILL_DIR/scripts/render_mermaid.py" "$md")"
  pandoc "$src" -o "$out" --pdf-engine=weasyprint -s \
    --template="$SKILL_DIR/assets/$style.html" \
    --css="$SKILL_DIR/assets/$style.css"
  [ "$src" != "$md" ] && rm -f "$src"
  echo "wrote $out"
done
