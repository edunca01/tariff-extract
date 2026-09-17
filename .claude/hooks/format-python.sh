#!/usr/bin/env bash
# PostToolUse hook on Edit|Write: keep Python files ruff-clean as they are written,
# so `make check` never fails on formatting. Silent no-op for non-Python files or if uv is absent.
set -euo pipefail
input=$(cat)
file=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)
case "$file" in
  *.py) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0
command -v uv >/dev/null 2>&1 || exit 0
cd "${CLAUDE_PROJECT_DIR:-.}"
uv run --quiet ruff check --fix --quiet "$file" >/dev/null 2>&1 || true
uv run --quiet ruff format --quiet "$file" >/dev/null 2>&1 || true
exit 0
