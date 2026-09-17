#!/usr/bin/env python3
"""PreToolUse hook on Bash for a public repo with one human author.

Reads the tool call as JSON on stdin and refuses (exit 2) git invocations that would:
  1. commit a message carrying an AI attribution trailer
  2. commit directly on main
  3. force-push, or push to main
  4. stage .env or corpus PDFs outside corpus/demo
Only command segments whose first word is `git` are inspected, and heredoc bodies are
stripped first, so file contents that merely mention git never trigger it.
Everything else exits 0 and falls through to the normal permission flow.
"""

import json
import os
import re
import subprocess
import sys

HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\1(?=\n|$)", re.S)
SEPARATORS = re.compile(r"&&|\|\||;|\n|(?<!\|)\|(?!\|)")
ATTRIBUTION = re.compile(r"co-authored-by|claude-session|generated with|🤖", re.I)


def deny(msg: str) -> None:
    print(f"guard-git: {msg}", file=sys.stderr)
    sys.exit(2)


def on_main() -> bool:
    root = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    r = subprocess.run(
        ["git", "-C", root, "symbolic-ref", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return r.returncode == 0 and r.stdout.strip() == "main"


def main() -> None:
    try:
        cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except Exception:
        return
    if not cmd:
        return
    cmd = HEREDOC.sub("\n", cmd)
    for raw in SEPARATORS.split(cmd):
        seg = re.sub(r"^[\s(]*(sudo\s+)?", "", raw.strip())
        if not re.match(r"git(\s|$)", seg):
            continue
        if re.match(r"git\s+commit\b", seg):
            # -m messages may span lines; scan the whole (heredoc-stripped) command.
            if ATTRIBUTION.search(cmd):
                deny("commit message contains an AI attribution trailer. Drop it; one human author.")
            if on_main():
                deny("refusing to commit on main. Create a branch: git switch -c feat/<slug>")
        if re.match(r"git\s+push\b", seg):
            if re.search(r"--force|(^|\s)-f(\s|$)|\s\+\S", seg):
                deny("force-push is not allowed.")
            if re.search(r"\smain(\s|$)|HEAD:main", seg):
                deny("pushing to main directly is not allowed; open a PR.")
        if re.match(r"git\s+add\b", seg):
            if re.search(r"(^|[\s/])\.env(\s|$)", seg):
                deny(".env must never be staged.")
            if "corpus/pdfs/" in seg:
                deny("corpus PDFs are a release asset, not a git object. Only corpus/demo/ is committed.")


if __name__ == "__main__":
    main()
