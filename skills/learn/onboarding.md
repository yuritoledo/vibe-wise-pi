# Onboarding

Guide one step at a time. Reuse answers already given; don't dump a questionnaire.
- Reuse completed global answers and project answers from their resolved files.
- A missing worktree progress file does not make onboarding incomplete.
- If a record says `Onboarding reset: pending`, reuse only post-reset answers for that record. Keep the marker until that record completes. Shared-mode reset preserves global preferences; legacy reset clears the combined profile.
For onboarding choices, call the host's structured-question tool with exactly one
question, 2–4 short options, brief descriptions, a header of at most 12 characters,
and `multiSelect: false`.
Use its native keyboard picker, not a printed imitation. If unavailable, ask one
plain-text question. Open-ended answers belong in chat.

Briefly explain: learning comes first. Ask for their approach, then give feedback,
explain unfamiliar concepts, and ask follow-ups where needed. Their reasoning shapes
the design; AI writes the agreed implementation. Suggestions aren't an automatic next step.
- Notes use the paths resolved by SKILL.md. Only worktree progress stays in `.vibe-wise/` for new shared setups.
- Recommend ignoring the local state directory in Git. Change `.gitignore` only when requested; announce the edit first.

## Project

Unless already answered, first ask “What are we doing?” using a native picker:
New project / Existing repo / Known project. Don't infer the answer from an empty
folder. Wait for each answer before the next question.

- **New:** Ask what they're building if unknown. Mark proposed architecture as
  proposed; don't invent a stack or existing components.
- **Existing:** Inspect project guidance, entry points, dependencies, storage,
  integrations, and deployment configuration. Avoid secrets and generated files.
  Save a small evidence-based map and show a concise flow with unknowns. Then ask
  codebase familiarity (New / A little experience / Know it well), followed by
  learning scope (Whole system / Parts we touch / A mix), in separate pickers.
- **Known:** Ask architecture familiarity if unknown. Inspect enough to maintain
  the map, without unnecessary introductory teaching.

## Learner

Ask only what's unknown, one question at a time:

- Programming experience: Beginner / Intermediate / Advanced. Save it with preferences in the global profile. Reuse it across projects.
- Stack familiarity: Beginner / Intermediate / Advanced. Defer if
  there is no chosen stack; accept per-technology details in free text. Save stack familiarity and goals in project settings, not the global profile.
  Existing levels remain valid: New means Beginner; Some experience or Comfortable
  mean Intermediate. Don't repeat onboarding just to update a label.
- Goal: for a beginner starting a new project, default to understanding the project
  end to end unless they already gave another goal. Say “I'll guide you through
  how this project works end to end as we build it.” Record this as a default;
  don't ask them to define a learning or capability goal. They can change it later.
  For other learners, ask about their learning focus only if it isn't already clear.
- Preferences, a native picker:
  - Use defaults — Reason through each meaningful decision first; AI writes code.
  - Customize — Adjust frequency, question style, or who writes the code.

Defaults means Normal checkpoints and open-ended reasoning. Finish preference setup immediately; continue only any unanswered project questions.
Customize asks frequency (Light / Normal /
Frequent), reasoning style (Open-ended / Multiple choice / Mixed), and coding
preference (AI writes / A mix / More hands-on), each in a separate picker. Reasoning
style doesn't change setup pickers. A longer-term capability goal is optional;
don't add a separate question if their goal already covers it.

If they want to skip setup, use existing preferences or defaults, mark unknown answers Not specified, and proceed. Save each record's known answers with state-templates.md. Use `Onboarding: incomplete` and a short Remaining onboarding list only for the record that still needs answers. Mark each record complete independently.
Self-reported experience isn't demonstrated understanding. Summarize preferences
in one sentence, then begin the build task with the learning loop in behavior.md.
