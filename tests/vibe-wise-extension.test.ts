import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, realpath, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

import vibeWise, {
  buildRestorationContext,
  findActiveState,
} from "../extensions/vibe-wise/index.ts";

type Handler = (event: unknown, context: ExtensionContext) => unknown;

async function project(name: string) {
  const root = await import("node:fs/promises").then(({ mkdtemp }) =>
    mkdtemp(path.join(tmpdir(), `${name}-`)),
  );
  await mkdir(path.join(root, ".git"));
  return root;
}

async function notes(root: string, mode = "active") {
  const state = path.join(root, ".vibe-wise");
  await mkdir(state);
  await writeFile(
    path.join(state, "profile.md"),
    `# Learner Profile\nLearning mode: ${mode}\nOnboarding: complete\n`,
  );
  await writeFile(path.join(state, "progress.md"), "# Learning Progress\n");
  await writeFile(path.join(state, "project-map.md"), "# Project Map\n");
  return state;
}

function harness() {
  const handlers = new Map<string, Handler>();
  const sent: Array<{ message: unknown; options: unknown }> = [];
  const api = {
    on(event: string, handler: Handler) {
      handlers.set(event, handler);
      return () => handlers.delete(event);
    },
    sendMessage(message: unknown, options: unknown) {
      sent.push({ message, options });
    },
  } as unknown as ExtensionAPI;
  vibeWise(api);
  return { handlers, sent };
}

function context(cwd: string) {
  return { cwd } as ExtensionContext;
}

test("finds the nearest active state without crossing a Git boundary", async () => {
  const root = await project("vibe-wise-state");
  const state = await notes(root);
  const nested = path.join(root, "src", "services");
  await mkdir(nested, { recursive: true });

  assert.equal(findActiveState(nested), await realpath(state));

  const worktree = path.join(root, "worktree");
  await mkdir(worktree);
  await writeFile(path.join(worktree, ".git"), "gitdir: elsewhere");
  assert.equal(findActiveState(worktree), null);
});

test("rejects paused and symlinked state", async () => {
  const pausedRoot = await project("vibe-wise-paused");
  await notes(pausedRoot, "paused");
  assert.equal(findActiveState(pausedRoot), null);

  const linkedRoot = await project("vibe-wise-linked");
  const outside = await project("vibe-wise-outside");
  const outsideState = await notes(outside);
  await symlink(outsideState, path.join(linkedRoot, ".vibe-wise"), "dir");
  assert.equal(findActiveState(linkedRoot), null);
});

test("builds constant restoration instructions with the Pi skill path", async () => {
  const root = await project("vibe-wise-context");
  const state = await notes(root);
  await writeFile(path.join(state, "progress.md"), "x".repeat(100_000));

  const restoration = buildRestorationContext(state);

  assert.match(restoration, /VibeWise is active/);
  assert.match(restoration, /skills\/learn\/SKILL\.md/);
  assert.ok(restoration.includes(state));
  assert.match(restoration, /Search the entire progress\.md/);
  assert.ok(restoration.length < 10_000);
  assert.doesNotMatch(restoration, /x{100}/);
});

test("injects restoration once when an active Pi session starts", async () => {
  const root = await project("vibe-wise-session");
  const state = await notes(root);
  const extension = harness();

  await extension.handlers.get("session_start")?.(
    { type: "session_start", reason: "startup" },
    context(root),
  );
  const first = (await extension.handlers.get("before_agent_start")?.(
    { type: "before_agent_start", prompt: "continue" },
    context(root),
  )) as { message?: { content: string; display: boolean } } | undefined;
  const second = await extension.handlers.get("before_agent_start")?.(
    { type: "before_agent_start", prompt: "continue" },
    context(root),
  );

  assert.equal(first?.message?.display, false);
  assert.ok(first?.message?.content.includes(state));
  assert.equal(second, undefined);
});

test("restores again after compaction and tree navigation", async () => {
  const root = await project("vibe-wise-lifecycle");
  const state = await notes(root);
  const extension = harness();

  await extension.handlers.get("session_start")?.(
    { type: "session_start", reason: "startup" },
    context(root),
  );
  await extension.handlers.get("before_agent_start")?.(
    { type: "before_agent_start", prompt: "start" },
    context(root),
  );
  await extension.handlers.get("session_compact")?.(
    { type: "session_compact", reason: "manual" },
    context(root),
  );

  assert.equal(extension.sent.length, 1);
  assert.ok(
    (extension.sent[0]?.message as { content: string }).content.includes(state),
  );
  assert.deepEqual(extension.sent[0]?.options, { triggerTurn: false });

  await extension.handlers.get("session_tree")?.(
    { type: "session_tree", newLeafId: "new", oldLeafId: "old" },
    context(root),
  );
  const afterTree = (await extension.handlers.get("before_agent_start")?.(
    { type: "before_agent_start", prompt: "continue" },
    context(root),
  )) as { message?: { content: string } } | undefined;
  assert.match(afterTree?.message?.content ?? "", /VibeWise is active/);
});

test("does not inject context for inactive projects", async () => {
  const root = await project("vibe-wise-inactive");
  const extension = harness();

  await extension.handlers.get("session_start")?.(
    { type: "session_start", reason: "startup" },
    context(root),
  );
  const result = await extension.handlers.get("before_agent_start")?.(
    { type: "before_agent_start", prompt: "start" },
    context(root),
  );
  await extension.handlers.get("session_compact")?.(
    { type: "session_compact", reason: "manual" },
    context(root),
  );

  assert.equal(result, undefined);
  assert.equal(extension.sent.length, 0);
});


test("Pi restores shared onboarding for a fresh worktree without creating local notes", async (t) => {
  const { mkdtemp, rm, access } = await import("node:fs/promises");
  const root = await realpath(await mkdtemp(path.join(tmpdir(), "vibe-wise-shared-")));
  const previous = process.env.XDG_CONFIG_HOME;
  process.env.XDG_CONFIG_HOME = path.join(root, "config");
  t.after(async () => {
    if (previous === undefined) delete process.env.XDG_CONFIG_HOME;
    else process.env.XDG_CONFIG_HOME = previous;
    await rm(root, { recursive: true, force: true });
  });
  const repo = path.join(root, "repo");
  const worktree = path.join(root, "worktree");
  execFileSync("git", ["init", "-q", repo]);
  execFileSync("git", ["-C", repo, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-qm", "init"]);
  execFileSync("git", ["-C", repo, "worktree", "add", "-qb", "topic", worktree]);
  const key = createHash("sha256").update(await realpath(path.join(repo, ".git"))).digest("hex");
  const shared = path.join(process.env.XDG_CONFIG_HOME, "vibe-wise");
  const project = path.join(shared, "projects", key);
  await mkdir(project, { recursive: true });
  await writeFile(path.join(shared, "profile.md"), "Onboarding: complete\nOverall programming: Advanced\n");
  await writeFile(path.join(project, "project.md"), "Learning mode: active\nOnboarding: complete\n");
  const extension = harness();
  await extension.handlers.get("session_start")?.({}, context(worktree));
  const result = await extension.handlers.get("before_agent_start")?.({}, context(worktree)) as { message?: { content: string } };
  assert.ok(result?.message?.content.includes(path.join(shared, "profile.md")));
  assert.ok(result?.message?.content.includes(path.join(project, "project-map.md")));
  assert.ok(result?.message?.content.includes(path.join(worktree, ".vibe-wise", "progress.md")));
  await assert.rejects(access(path.join(worktree, ".vibe-wise")));
  await writeFile(path.join(project, "project.md"), "Learning mode: paused\n");
  await extension.handlers.get("session_tree")?.({}, context(worktree));
  assert.equal(await extension.handlers.get("before_agent_start")?.({}, context(worktree)), undefined);
});
