#!/usr/bin/env bash
# Exportify YouTube Downloader - Quick Launcher
#
# If 'exportifydl' is installed, this just calls it.
# Otherwise, falls back to running main.py directly.
#
# Install the command globally:  pip install -e .
# Then use:  exportifydl run

set -e

# If exportifydl is already installed, use it
if command -v exportifydl &>/dev/null; then
    exec exportifydl "$@"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-detect python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Error: Python 3 is required but not found."
    echo "Install it with: sudo dnf install python3"
    exit 1
fi

# Check for required dependencies
missing=()
for pkg in rich yt_dlp mutagen PIL; do
    if ! "$PYTHON" -c "import $pkg" 2>/dev/null; then
        missing+=("$pkg")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo "Missing Python packages detected. Installing..."
    "$PYTHON" -m pip install --user -r requirements.txt
    echo ""
    echo "Installing exportifydl command..."
    "$PYTHON" -m pip install --user -e .
    echo ""
    # Now it should be installed
    if command -v exportifydl &>/dev/null; then
        exec exportifydl "$@"
    fi
fi

exec "$PYTHON" main.py "$@"
