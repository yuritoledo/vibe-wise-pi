"""Preview by default; reset only a confirmed snapshot of local learning notes."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from state import resolve_state, safe_path


FRESH = {
    "profile.md": (
        "# Learner Profile\n\nLearning mode: active\nOnboarding: incomplete\n"
        "Onboarding reset: pending\n\n"
        "Remaining onboarding: Project situation, experience, stack familiarity, "
        "goals, and preferences.\n"
    ),
    "progress.md": "# Learning Progress\n\nNo learning events recorded yet.\n",
    "project-map.md": "# Project Map\n\nNot mapped yet. Inspect the current project.\n",
}


def reset_targets(cwd):
    files = resolve_state(cwd)
    if files is None:
        return None, {}
    state = Path(files["state"])
    if files["kind"] == "legacy":
        return state, {name: (state / name, text) for name, text in FRESH.items()}
    return state, {
        "project.md": (Path(files["project"]), "# Project Settings\n\nLearning mode: active\nOnboarding: incomplete\nOnboarding reset: pending\nRemaining onboarding: Project familiarity, stack familiarity, and goals.\n"),
        "project-map.md": (Path(files["map"]), FRESH["project-map.md"]),
        "progress.md": (Path(files["progress"]), FRESH["progress.md"]),
    }


def snapshot(cwd):
    state, targets = reset_targets(cwd)
    if state is None:
        return None, {}, None
    notes = {}
    digest = hashlib.sha256(str(state).encode())
    for name, (path, _text) in targets.items():
        if not safe_path(path):
            raise ValueError("Refusing to reset non-regular note: " + str(path))
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            data = None
        else:
            if not stat.S_ISREG(mode):
                raise ValueError("Refusing to reset non-regular note: " + str(path))
            data = path.read_bytes()
            notes[name] = data
        digest.update(json.dumps([str(path), None if data is None else data.hex()]).encode())
    return state, notes, digest.hexdigest()


def reset(cwd, confirmation=None):
    cwd = Path(cwd)
    if not cwd.is_absolute() or not cwd.is_dir():
        raise ValueError("Use an existing absolute project working directory.")
    cwd = cwd.resolve()
    state, notes, fingerprint = snapshot(cwd)
    if confirmation is not None and (not notes or confirmation != fingerprint):
        raise ValueError("Target or notes changed. Preview and confirm again; nothing reset.")
    if not notes:
        return {"status": "no_notes", "cwd": str(cwd)}
    targets = reset_targets(cwd)[1]
    result = {
        "status": "preview", "project": str(state.parent), "state": str(state),
        "files": list(notes), "backup_parent": str(state / "backups"),
        "targets": {name: str(path) for name, (path, _text) in targets.items()},
        "scope": "project settings and map (all linked worktrees), and current worktree progress; global preferences stay unchanged" if "project.md" in targets else "local learning notes",
        "confirmation": fingerprint,
    }
    if confirmation is None:
        return result

    backup_parent = state / "backups"
    if backup_parent.is_symlink() or (backup_parent.exists() and not backup_parent.is_dir()):
        raise ValueError("Backup path must be a real directory; nothing reset.")
    backup_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    prefix = datetime.now(timezone.utc).strftime("reset-%Y%m%dT%H%M%SZ-")
    backup = Path(tempfile.mkdtemp(prefix=prefix, dir=backup_parent))
    replacements = {}
    try:
        # Finish all backups and prepare replacements before touching active notes.
        for name, data in notes.items():
            (backup / name).write_bytes(data)
        if "project.md" in targets:
            (backup / "targets.json").write_text(json.dumps(result["targets"], indent=2), encoding="utf-8")
        for name, (path, text) in targets.items():
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            # Stage beside the target: shared config may be on a different volume.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=".reset-", delete=False) as staged:
                replacements[name] = Path(staged.name)
                staged.write(text)
        if snapshot(cwd)[2] != fingerprint:
            raise ValueError("Notes changed during backup; active notes were not reset.")
        for name, (path, _text) in targets.items():
            os.replace(replacements[name], path)
    except (OSError, ValueError) as error:
        raise ValueError(
            "Reset did not complete. Backup location: {}. "
            "Check active notes before continuing. {}".format(backup, error)
        ) from error
    finally:
        for staged in replacements.values():
            staged.unlink(missing_ok=True)
    return {"status": "reset", "project": str(state.parent),
            "state": str(state), "backup": str(backup)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--confirm", help="Snapshot token from a preview; only after user confirmation")
    args = parser.parse_args()
    try:
        result = reset(args.cwd, args.confirm)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "error", "message": str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
