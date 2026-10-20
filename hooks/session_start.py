"""Restore resolved learning context for Claude Code without changing notes."""

import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from state import resolve_state, restoration_context


def restore(payload):
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "SessionStart":
        return None
    raw_cwd = payload.get("cwd")
    if not isinstance(raw_cwd, str) or not Path(raw_cwd).is_absolute():
        return None
    files = resolve_state(raw_cwd)
    if not files or not files["active"]:
        return None
    return {"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": restoration_context(files, PLUGIN_ROOT / "skills/learn/SKILL.md"),
    }}


def main():
    try:
        payload = json.loads(sys.stdin.read(65536))
        output = restore(payload)
    except (OSError, ValueError, TypeError, RecursionError):
        return  # Learning must not prevent a coding session from starting.
    if output:
        print(json.dumps(output))


if __name__ == "__main__":
    main()
