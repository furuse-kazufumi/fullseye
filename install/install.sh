#!/usr/bin/env bash
#
# Fullseye + Fullseye Studio installer for Linux / macOS.
#
# By default this script:
#   1. Finds a Python 3.11 (or 3.10+) interpreter.
#   2. Creates a virtual environment at <repo>/.venv (skipped if it exists).
#   3. Installs Fullseye in editable mode with the requested extras.
#   4. Installs a "Fullseye Studio" launcher into
#      ~/.local/share/applications/ (skipped with --no-shortcut).
#
# It is idempotent: re-running reuses the venv, upgrades the install and
# rewrites the .desktop entry. It never asks interactive questions.
#
# Usage:
#   bash install/install.sh [options]
#
# Options:
#   --minimal          Install only the "gui" extra (core + PySide6 GUI).
#   --extras "a,b"     Comma-separated pip extras (default: all,gui).
#   --user-site        pip install --user instead of a venv.
#   --no-shortcut      Do not create the .desktop launcher.
#   --repo <path>      Repository root (default: parent of this script's dir).
#   -h, --help         Show this help.
#
set -euo pipefail

# --------------------------------------------------------------------------- #
# Defaults and argument parsing.
# --------------------------------------------------------------------------- #
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
EXTRAS="all,gui"
USER_SITE=0
NO_SHORTCUT=0

usage() {
    sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --minimal)      EXTRAS="gui"; shift ;;
        --extras)       EXTRAS="$2"; shift 2 ;;
        --user-site)    USER_SITE=1; shift ;;
        --no-shortcut)  NO_SHORTCUT=1; shift ;;
        --repo)         REPO_ROOT="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *) echo "Unknown option: $1" >&2; echo "Run with --help for usage." >&2; exit 2 ;;
    esac
done

# Normalise the repo root to an absolute path.
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"

if [ ! -f "$REPO_ROOT/pyproject.toml" ]; then
    echo "ERROR: pyproject.toml not found under '$REPO_ROOT'." >&2
    echo "Pass the repository root with --repo <path>." >&2
    exit 1
fi
if [ ! -f "$REPO_ROOT/studio.py" ]; then
    echo "ERROR: studio.py not found under '$REPO_ROOT'. Is this the Fullseye repo?" >&2
    exit 1
fi

echo "Fullseye installer"
echo "Repository: $REPO_ROOT"

# --------------------------------------------------------------------------- #
# 1. Locate a suitable Python interpreter (3.11 preferred, 3.10+ accepted).
# --------------------------------------------------------------------------- #
PYTHON=""
for cand in python3.11 python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        # Require >= 3.10 (matches pyproject requires-python).
        if "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)' 2>/dev/null; then
            PYTHON="$(command -v "$cand")"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "" >&2
    echo "ERROR: No Python 3.10+ interpreter found (looked for python3.11, python3, python)." >&2
    echo "Install Python 3.11, e.g.:" >&2
    echo "  Debian/Ubuntu : sudo apt install python3.11 python3.11-venv" >&2
    echo "  Fedora        : sudo dnf install python3.11" >&2
    echo "  macOS (brew)  : brew install python@3.11" >&2
    echo "  Or download   : https://www.python.org/downloads/" >&2
    exit 1
fi
echo "Using Python: $PYTHON ($("$PYTHON" --version 2>&1))"
echo "Extras: [$EXTRAS]"

# The editable target - brackets select the extras, kept as one argument.
PIP_TARGET="${REPO_ROOT}[${EXTRAS}]"

# --------------------------------------------------------------------------- #
# 2. Install (venv by default, or --user site).
# --------------------------------------------------------------------------- #
VENV_DIR="$REPO_ROOT/.venv"

if [ "$USER_SITE" -eq 1 ]; then
    echo ""
    echo "== Installing into user site-packages =="
    "$PYTHON" -m pip install --user -U pip
    "$PYTHON" -m pip install --user -e "$PIP_TARGET"
    DESKTOP_PYTHON="$PYTHON"
else
    echo ""
    echo "== Preparing virtual environment =="
    if [ -x "$VENV_DIR/bin/python" ]; then
        echo "Reusing existing venv: $VENV_DIR"
    else
        echo "Creating venv: $VENV_DIR"
        "$PYTHON" -m venv "$VENV_DIR"
    fi
    echo ""
    echo "== Installing Fullseye (editable) =="
    "$VENV_DIR/bin/python" -m pip install -U pip
    "$VENV_DIR/bin/python" -m pip install -e "$PIP_TARGET"
    DESKTOP_PYTHON="$VENV_DIR/bin/python"
fi

# --------------------------------------------------------------------------- #
# 3. Install the .desktop launcher (unless suppressed).
# --------------------------------------------------------------------------- #
if [ "$NO_SHORTCUT" -eq 0 ]; then
    echo ""
    echo "== Installing desktop launcher =="
    TEMPLATE="$SCRIPT_DIR/fullseye-studio.desktop"
    APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    DEST="$APPS_DIR/fullseye-studio.desktop"
    mkdir -p "$APPS_DIR"

    if [ ! -f "$TEMPLATE" ]; then
        echo "WARNING: template '$TEMPLATE' missing; skipping launcher." >&2
    else
        # Substitute the interpreter and repo placeholders. '|' is used as the
        # sed delimiter so that paths containing '/' need no escaping.
        sed -e "s|@PYTHON@|$DESKTOP_PYTHON|g" \
            -e "s|@REPO@|$REPO_ROOT|g" \
            "$TEMPLATE" > "$DEST"
        chmod 644 "$DEST"
        echo "Installed: $DEST"
        echo "  Exec = $DESKTOP_PYTHON $REPO_ROOT/studio.py"

        # Refresh the desktop database if the tool is available (best-effort).
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
        fi
    fi
fi

# --------------------------------------------------------------------------- #
# 4. Done - how to launch.
# --------------------------------------------------------------------------- #
echo ""
echo "== Installation complete =="
echo "Launch Fullseye Studio:"
echo "  - Application menu entry:  'Fullseye Studio'"
if [ "$USER_SITE" -eq 1 ]; then
    echo "  - Console script:          fullseye-studio"
    echo "  - Direct:                  $PYTHON $REPO_ROOT/studio.py"
    echo ""
    echo "CLI (Fullseye):  fullseye --help"
else
    echo "  - Console script:          $VENV_DIR/bin/fullseye-studio"
    echo "  - Direct:                  $VENV_DIR/bin/python $REPO_ROOT/studio.py"
    echo ""
    echo "CLI (Fullseye):  $VENV_DIR/bin/fullseye --help"
fi
echo ""
