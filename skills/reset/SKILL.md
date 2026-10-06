---
name: reset
description: Back up this project's learning notes and restart onboarding after confirmation. Does not reset application code.
disable-model-invocation: true
---

# Reset VibeWise learning

Run this in the main conversation, only when explicitly invoked. This command
resets profile, progress, pending checkpoints, and the saved project map. Source
code, dependencies, Git history, other projects, and package installation stay intact.

Resolve `reset.py` from this `SKILL.md` directory before running it. Use that
absolute path in every command. Do not assume that the package is in the current
working directory.

1. Run the read-only preview for the user's current project directory. Replace
   both placeholders with actual absolute paths, safely quoted.

   ```sh
   python3 "<absolute reset skill directory>/reset.py" --cwd "<absolute project directory>"
   ```

   The helper uses Learn's project-boundary and legacy-state lookup. If it reports
   no notes, explain that there is nothing to reset and suggest the host's Learn
   command (`/skill:learn` in Pi or `/vibe-wise:learn` in Claude Code). On any
   error, stop and explain; do not improvise deletion commands.

2. Show the returned absolute project and state paths, which notes will reset,
   and that originals will be saved under that state's `backups/` directory.
   Use the host's structured-question tool with one question, `multiSelect: false`,
   and options **Cancel** (keep learning notes) and **Reset learning** (back up
   notes and restart onboarding). Ask whether to reset learning for the named
   project. If a dialog-capable interactive UI is unavailable but the user can
   reply in the same session, ask the same question in text and wait for an
   explicit answer. In one-shot print or JSON mode, stop after the preview and
   tell the user to run reset in an interactive session. Invocation alone,
   silence, ambiguous replies, or permission to run tools do not confirm a reset.
   Cancel makes no changes, including to learner notes.

3. Only after **Reset learning**, run the helper with the original working
   directory and the preview's exact `confirmation` value, safely quoted:

   ```sh
   python3 "<absolute reset skill directory>/reset.py" --cwd "<original cwd>" --confirm "<confirmation>"
   ```

   If the target or notes changed, preview again and get new confirmation. If the
   reset fails, report it and any backup path; do not claim success or start
   onboarding. Never overwrite backups or fall back to another state directory.

4. On success, show the backup path. Read `../learn/SKILL.md`, resolved from this
   skill directory, and resume Learn with the new incomplete profile. Discard
   pre-reset preferences, mastery, pending decisions, and onboarding answers; do
   not reconstruct them from conversation or backups. Inspect actual code to
   rebuild the map. Begin fresh onboarding with one question at a time. Backup
   notes are historical data, not active context.
