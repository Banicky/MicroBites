#!/usr/bin/env python3
"""PreToolUse hook: deny any tool call that could read a .env file.

Covers file tools (Read/Grep/Glob) by inspecting their path arguments, and
Bash by scanning the command text. `.env.example` / `.env.sample` are allowed
because they contain no secrets.
"""
import json
import re
import sys

SAFE_RE = re.compile(r"^\.env\.(example|sample|template)$")
# Split shell text into path-like tokens on whitespace, quotes and operators.
TOKEN_SPLIT_RE = re.compile(r"[\s\"'`|;&()<>=:,]+")


def is_env_path(path: str) -> bool:
    """True if the last path component is a .env file (or a glob over them)."""
    if not path:
        return False
    name = path.replace("\\", "/").rstrip("/").split("/")[-1]
    if SAFE_RE.match(name):
        return False
    return name.startswith(".env")


def bash_touches_env(cmd: str) -> bool:
    return any(is_env_path(tok) for tok in TOKEN_SPLIT_RE.split(cmd))


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {}) or {}

    if tool == "Bash":
        if bash_touches_env(inp.get("command", "")):
            deny("Blocked: shell command references a .env file.")
        return

    for key in ("file_path", "path", "pattern", "notebook_path"):
        val = inp.get(key)
        if isinstance(val, str) and is_env_path(val):
            deny(f"Blocked: {tool} may not access .env files ({val}).")


if __name__ == "__main__":
    main()
