#!/usr/bin/env bash
# pre-commit hook: the test split must not be opened during prompt iteration (spec R1.3).
# A commit that touches prompts/ AND labels/gold/ files belonging to the test split is refused.
set -euo pipefail
splits="labels/splits.json"
[ -f "$splits" ] || exit 0
staged=$(git diff --cached --name-only)
echo "$staged" | grep -q '^prompts/' || exit 0
test_ids=$(python3 -c "import json;print('\n'.join(json.load(open('$splits')).get('test',[])))" 2>/dev/null || true)
[ -n "$test_ids" ] || exit 0
for id in $test_ids; do
  if echo "$staged" | grep -q "^labels/gold/$id\.json$"; then
    echo "pre-commit: commit touches prompts/ and test-split label $id. Separate the commits." >&2
    exit 1
  fi
done
