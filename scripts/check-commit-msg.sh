#!/usr/bin/env bash
# commit-msg hook: this is a public repo with a single human author.
# Reject any trailer or badge that attributes the commit to an AI tool,
# regardless of which tool produced the message.
set -euo pipefail
msg_file="$1"
if grep -Ei 'co-authored-by:.*(claude|anthropic|copilot|chatgpt|openai|gemini|cursor)|claude-session:|generated with \[?claude code|🤖 generated with' "$msg_file" >/dev/null; then
  echo "commit-msg: AI attribution trailer found. Remove Co-Authored-By/Claude-Session/Generated-with lines." >&2
  exit 1
fi
