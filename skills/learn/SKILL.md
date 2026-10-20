---
name: learn
description: Activate or resume learning-first development. You lead the design; the coding agent gives feedback, explains concepts, asks follow-ups, and writes the agreed code.
disable-model-invocation: true
---

# VibeWise Learn mode

- Activate learning mode in the main conversation. Read [behavior.md](behavior.md) and follow it throughout development.
- Ask for the learner's approach and wait. Give concise feedback on their reasoning. Explain unfamiliar concepts as needed.
- Offer approaches when they ask for help or are stuck. Return decisions to them.
- An ordinary build request retains this loop. Only an explicit request to skip or pause bypasses it.
- Do not switch to a subagent or require manual coding by default.
- Use the host's file reader for package guides. Discover optional state files before reading them. Missing files are normal setup, not an error.

## Resolve state

1. Resolve `../../hooks/state.py` from this skill directory. Run the read-only resolver with the user's absolute working directory, safely quoted:

   ```sh
   python3 -B "<absolute package directory>/hooks/state.py" --cwd "<absolute working directory>"
   ```

2. Use the returned absolute paths, not paths inferred from this document. A null result means invalid or linked state. Explain the problem and stop state setup; do not select another directory.

   - `kind: legacy` keeps an existing local profile in place. `profile` and `project` point to the same file. Keep its combined onboarding format. Never migrate, merge, or reset notes automatically.
   - `kind: shared` uses a global learner `profile`, project settings in `project`, a project `map`, and worktree-local `progress`.
   - The resolver uses `$XDG_CONFIG_HOME/vibe-wise`, or `~/.config/vibe-wise` when unset or relative. Git's resolved common directory identifies the project. Linked worktrees share settings and the map. Separate clones and submodules stay separate. Without Git, the selected local state root or current directory identifies the project.
   - Local `.vibe-wise/profile.md` or legacy `.sensible-vibes/profile.md` takes precedence, even when paused. A directory with only progress does not override shared onboarding.
   - Discovery stops at the nearest Git boundary. Never follow symlinked notes or directories. Recheck before writing.

3. Read each existing profile and project file once, then the map. Search the entire existing progress file for pending decisions. Read their full sections and relevant topics before continuing. Resume the recorded checkpoint stage; an initial excerpt does not establish that no decision is pending.

4. Explicit Learn may resume a paused project: set `Learning mode: active` in the resolved project file. Automatic restoration must keep a paused project paused. Global preferences alone never activate an unrelated project.

## Resume or onboard

- Reuse completed global answers and project onboarding. A fresh worktree with no progress file does not need onboarding again.
- Read [onboarding.md](onboarding.md) when either onboarding record is missing or incomplete. Ask only unanswered questions for that record.
- Use [state-templates.md](state-templates.md) when creating missing files. Create parent directories only during explicit setup. Preserve existing notes. Recreate missing maps from inspected code, not invented history.
- After setup, continue the user's task. If none was provided, ask what they want to build or change. Invoking Learn again never resets state.
