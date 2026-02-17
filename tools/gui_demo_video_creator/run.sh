#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
PYTHON_SCRIPT="$SCRIPT_DIR/gui_demo_video_creator.py"

if [ ! -d "$VENV_DIR" ]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$VENV_DIR"
  elif command -v python >/dev/null 2>&1; then
    python -m venv "$VENV_DIR"
  else
    echo "Python was not found on PATH. Install Python 3.10+ and retry." >&2
    exit 1
  fi
fi

if [ -x "$VENV_DIR/bin/python" ]; then
  VENV_PYTHON="$VENV_DIR/bin/python"
else
  VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
fi

"$VENV_PYTHON" -m pip install --upgrade pip
if [ -f "$REQUIREMENTS_FILE" ]; then
  "$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_FILE"
fi

"$VENV_PYTHON" "$PYTHON_SCRIPT" "$@"
