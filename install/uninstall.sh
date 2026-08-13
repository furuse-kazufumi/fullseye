#!/usr/bin/env bash
#
# Uninstaller for Fullseye + Fullseye Studio (Linux / macOS).
#
# Removes the "Fullseye Studio" .desktop launcher and uninstalls the `fullseye`
# package. If a project venv (<repo>/.venv) exists, the package is removed from
# it; otherwise it is removed from the user site-packages. The venv directory
# is kept unless --remove-venv is given. Idempotent - missing pieces are
# silently skipped.
#
# Usage:
#   bash install/uninstall.sh [--remove-venv] [--repo <path>]
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
REMOVE_VENV=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --remove-venv) REMOVE_VENV=1; shift ;;
        --repo)        REPO_ROOT="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: bash install/uninstall.sh [--remove-venv] [--repo <path>]"
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
echo "Fullseye uninstaller"
echo "Repository: $REPO_ROOT"

# --------------------------------------------------------------------------- #
# 1. Remove the .desktop launcher.
# --------------------------------------------------------------------------- #
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DEST="$APPS_DIR/fullseye-studio.desktop"
if [ -f "$DEST" ]; then
    rm -f "$DEST"
    echo "Removed launcher: $DEST"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
    fi
fi

# --------------------------------------------------------------------------- #
# 2. Uninstall the fullseye package (from venv if present, else user-site).
# --------------------------------------------------------------------------- #
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
if [ -x "$VENV_PYTHON" ]; then
    echo "Uninstalling 'fullseye' from venv..."
    "$VENV_PYTHON" -m pip uninstall fullseye -y || true
else
    PY="$(command -v python3.11 || command -v python3 || command -v python || true)"
    if [ -n "$PY" ]; then
        echo "Uninstalling 'fullseye' from user site-packages..."
        "$PY" -m pip uninstall fullseye -y || true
    else
        echo "No Python interpreter found; skipping pip uninstall." >&2
    fi
fi

# --------------------------------------------------------------------------- #
# 3. Optionally remove the venv.
# --------------------------------------------------------------------------- #
if [ "$REMOVE_VENV" -eq 1 ]; then
    VENV_DIR="$REPO_ROOT/.venv"
    if [ -d "$VENV_DIR" ]; then
        echo "Removing venv: $VENV_DIR"
        rm -rf "$VENV_DIR"
    fi
fi

echo ""
echo "Uninstall complete."
