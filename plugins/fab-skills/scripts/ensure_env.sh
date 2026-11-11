#!/usr/bin/env bash
# Source this (do not execute it) to activate the `science` conda env, creating it
# if the machine does not have it yet:
#
#   source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/ensure_env.sh"
#
# No absolute paths: conda is discovered at runtime, so this works on any machine
# and any conda flavour (miniforge, miniconda, anaconda, mambaforge, /opt/conda).

FAB_ENV_NAME="${FAB_ENV_NAME:-science}"
# Everything the fab-skills need: pandoc + weasyprint (md -> PDF),
# poppler (pdftoppm/pdftotext, lets the Read tool open PDFs), pymupdf (PDF text).
FAB_ENV_PKGS=(python=3.12 pandoc weasyprint poppler pymupdf)

_fab_conda_base() {
  if command -v conda >/dev/null 2>&1; then
    conda info --base && return 0
  fi
  if [ -n "${CONDA_EXE:-}" ] && [ -x "$CONDA_EXE" ]; then
    dirname "$(dirname "$CONDA_EXE")" && return 0
  fi
  local d
  for d in "$HOME/miniforge3" "$HOME/mambaforge" "$HOME/miniconda3" \
           "$HOME/anaconda3" "$HOME/micromamba" /opt/conda /usr/local/conda; do
    if [ -x "$d/bin/conda" ]; then
      echo "$d" && return 0
    fi
  done
  return 1
}

FAB_CONDA_BASE="$(_fab_conda_base)" || {
  echo "ensure_env.sh: no conda installation found; install miniforge first" >&2
  return 1 2>/dev/null || exit 1
}

# shellcheck disable=SC1091
source "$FAB_CONDA_BASE/etc/profile.d/conda.sh"

_fab_solver=conda
command -v mamba >/dev/null 2>&1 && _fab_solver=mamba

if ! conda env list | awk '{print $1}' | grep -qx "$FAB_ENV_NAME"; then
  echo "ensure_env.sh: conda env '$FAB_ENV_NAME' missing, creating it (first run only)..." >&2
  "$_fab_solver" create -y -n "$FAB_ENV_NAME" -c conda-forge "${FAB_ENV_PKGS[@]}" >&2 || {
    echo "ensure_env.sh: failed to create env '$FAB_ENV_NAME'" >&2
    return 1 2>/dev/null || exit 1
  }
fi

conda activate "$FAB_ENV_NAME" || {
  echo "ensure_env.sh: could not activate '$FAB_ENV_NAME'" >&2
  return 1 2>/dev/null || exit 1
}

# An interrupted create leaves the env registered but empty, which would otherwise
# activate fine and then fail deep inside a conversion. Verify the tools, not the name.
_fab_missing=()
for _fab_bin in python pandoc pdftoppm; do
  command -v "$_fab_bin" >/dev/null 2>&1 || _fab_missing+=("$_fab_bin")
done
python -c "import weasyprint" 2>/dev/null || _fab_missing+=(weasyprint)
python -c "import fitz" 2>/dev/null || _fab_missing+=(pymupdf)

if [ ${#_fab_missing[@]} -gt 0 ]; then
  echo "ensure_env.sh: '$FAB_ENV_NAME' is incomplete (missing: ${_fab_missing[*]}), repairing..." >&2
  "$_fab_solver" install -y -n "$FAB_ENV_NAME" -c conda-forge "${FAB_ENV_PKGS[@]}" >&2 || {
    echo "ensure_env.sh: could not install into '$FAB_ENV_NAME'." >&2
    echo "  If downloads stall at a few bytes/sec on WSL2, the path MTU is too high:" >&2
    echo "  resolve the interface with 'ip route show default', then" >&2
    echo "  'sudo ip link set dev <iface> mtu 1350' and retry." >&2
    return 1 2>/dev/null || exit 1
  }
  conda activate "$FAB_ENV_NAME"
fi

# The agent's Read tool runs outside this env and looks up pdftoppm on its own PATH,
# so activating the env is not enough to let it open PDFs. Expose just the two poppler
# binaries it needs via ~/.local/bin (usually on PATH). Symlinks only, nothing copied,
# and an existing pdftoppm is never overwritten.
_fab_bindir="$HOME/.local/bin"
if mkdir -p "$_fab_bindir" 2>/dev/null; then
  for _fab_bin in pdftoppm pdftotext; do
    if [ ! -e "$_fab_bindir/$_fab_bin" ] && [ -x "$CONDA_PREFIX/bin/$_fab_bin" ]; then
      ln -s "$CONDA_PREFIX/bin/$_fab_bin" "$_fab_bindir/$_fab_bin" 2>/dev/null &&
        echo "ensure_env.sh: linked $_fab_bin into $_fab_bindir (for PDF reading)" >&2
    fi
  done
fi
