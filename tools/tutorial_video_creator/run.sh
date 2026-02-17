#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
PYTHON_SCRIPT="$SCRIPT_DIR/tutorial_video_creator.py"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python was not found on PATH. Install Python 3.10+ and retry." >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Venv python executable was not found: $VENV_PY" >&2
  exit 1
fi

"$VENV_PY" -m pip install --upgrade pip >/dev/null
if [[ -f "$REQUIREMENTS_FILE" ]]; then
  "$VENV_PY" -m pip install -r "$REQUIREMENTS_FILE"
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found. Attempting system install..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y ffmpeg
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y ffmpeg
  elif command -v brew >/dev/null 2>&1; then
    brew install ffmpeg
  fi
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required. Install ffmpeg or pass --ffmpeg-path to the Python script." >&2
  exit 1
fi

exec "$VENV_PY" "$PYTHON_SCRIPT" "$@"
