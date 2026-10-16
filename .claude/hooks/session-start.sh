#!/bin/bash
set -euo pipefail

# Only run in Claude Code cloud sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

PY_VERSION="3.14"
VENV="$CLAUDE_PROJECT_DIR/.venv"

# Create a Python 3.14 venv with uv (downloads the interpreter if missing; idempotent)
if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --quiet uv
fi
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" --version | grep -q "^Python $PY_VERSION"; then
  rm -rf "$VENV"
  uv venv --python "$PY_VERSION" "$VENV"
fi

# Install test deps (includes pytest-homeassistant-custom-component, pysmarthashtag) + linter
uv pip install --python "$VENV/bin/python" -r requirements_test.txt ruff

# Persist venv for the session
{
  echo "export VIRTUAL_ENV=\"$VENV\""
  echo "export PATH=\"$VENV/bin:\$PATH\""
} >> "${CLAUDE_ENV_FILE:-/dev/null}"
