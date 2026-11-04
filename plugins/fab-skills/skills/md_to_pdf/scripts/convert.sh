#!/usr/bin/env bash
set -euo pipefail

# Converts each Markdown file to <name>.pdf next to the source. Sending to the tablet is the
# to_tablet skill's job (scripts/push.sh there).
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ $# -gt 0 ] || { echo "usage: convert.sh <file.md> [...]" >&2; exit 2; }

# conda is not on PATH by default; fall back to the known miniforge install
CONDA_BASE="${CONDA_BASE:-$(conda info --base 2>/dev/null || echo /home/fab/miniforge3)}"
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate secore

command -v pandoc >/dev/null || conda install -y -c conda-forge pandoc
python -c "import weasyprint" 2>/dev/null || conda install -y -c conda-forge weasyprint

for md in "$@"; do
  out="${md%.md}.pdf"
  src="$(python "$SKILL_DIR/scripts/render_mermaid.py" "$md")"
  pandoc "$src" -o "$out" --pdf-engine=weasyprint -s \
    --template="$SKILL_DIR/assets/template.html" \
    --css="$SKILL_DIR/assets/secore.css"
  [ "$src" != "$md" ] && rm -f "$src"
  echo "wrote $out"
done
