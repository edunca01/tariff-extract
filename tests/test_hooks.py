"""The repo hygiene hooks are part of the deliverable; test them like code."""

import json
import subprocess
from pathlib import Path

import pytest

GUARD = Path(".claude/hooks/guard-git.py")
MSG = Path("scripts/check-commit-msg.sh")


def guard(command: str) -> int:
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        [str(GUARD)], input=payload, capture_output=True, text=True, check=False
    ).returncode


@pytest.mark.parametrize(
    "cmd",
    [
        'git commit -m "feat: x\n\nCo-Authored-By: Claude <noreply@anthropic.com>"',
        "git push --force origin feat/x",
        "git push origin main",
        "cd /x && git add .env",
        "git add corpus/pdfs/a.pdf",
    ],
)
def test_guard_denies(cmd: str) -> None:
    assert guard(cmd) == 2


@pytest.mark.parametrize(
    "cmd",
    [
        "git status && git diff",
        "git push origin feat/x",
        "cat > f.md <<'EOF'\nNever `git add corpus/pdfs/` or use Co-Authored-By\nEOF\necho ok",
        'echo "git push origin main" > notes.txt',
        "ls -la",
    ],
)
def test_guard_allows(cmd: str) -> None:
    assert guard(cmd) == 0


@pytest.mark.parametrize(
    ("msg", "rc"),
    [
        ("feat(extract): pdf path\n", 0),
        ("feat: x\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n", 1),
        ("feat: x\n\nClaude-Session: https://claude.ai/code/session_x\n", 1),
        ("fix: y\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n", 1),
    ],
)
def test_commit_msg_hook(tmp_path: Path, msg: str, rc: int) -> None:
    f = tmp_path / "COMMIT_EDITMSG"
    f.write_text(msg)
    assert subprocess.run([str(MSG), str(f)], capture_output=True, check=False).returncode == rc
