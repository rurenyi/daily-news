#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "error: python3 is required but was not found" >&2
  exit 1
fi

if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
else
  SUDO=""
fi

echo "==> Installing Ubuntu system packages"
$SUDO apt-get update
$SUDO apt-get install -y \
  ca-certificates \
  curl \
  fonts-noto-cjk \
  fonts-noto-color-emoji \
  fonts-noto-core \
  python3 \
  python3-pip \
  python3-venv

echo "==> Creating virtual environment at $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

echo "==> Installing Python dependencies"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e "$PROJECT_DIR"

echo "==> Installing Playwright Chromium and Linux dependencies"
"$VENV_DIR/bin/python" -m playwright install --with-deps chromium

echo "==> Creating runtime directories"
mkdir -p "$PROJECT_DIR/data"

echo
echo "Bootstrap completed."
echo "Next steps:"
echo "  1. Copy config.example.json to config.json and adjust settings"
echo "  2. Export DASHSCOPE_API_KEY"
echo "  3. Run: $VENV_DIR/bin/daily-news run-once --config $PROJECT_DIR/config.json --skip-publish"
