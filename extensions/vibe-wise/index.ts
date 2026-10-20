import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

// Use one resolver for Pi, Claude Code, explicit Learn, and reset.
function resolve(cwd: string, context = false): unknown {
  try {
    return JSON.parse(execFileSync(
      "python3",
      ["-B", path.join(PACKAGE_ROOT, "hooks", "state.py"), "--cwd", cwd, ...(context ? ["--context"] : [])],
      { encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "pipe"] },
    ));
  } catch {
    return null; // Optional learning context must not block a coding session.
  }
}

export function findActiveState(cwd: string): string | null {
  const files = resolve(cwd) as { active?: boolean; state?: string } | null;
  return files?.active && typeof files.state === "string" ? files.state : null;
}

export function buildRestorationContext(cwd: string): string {
  const content = resolve(cwd, true);
  return typeof content === "string" ? content : "";
}

function restorationMessage(content: string) {
  return {
    customType: "vibe-wise-restoration",
    content,
    display: false,
  };
}

export default function vibeWise(pi: ExtensionAPI): void {
  let pendingRestoration: string | null = null;

  function refresh(cwd: string) {
    pendingRestoration = buildRestorationContext(cwd);
  }

  pi.on("session_start", (_event, ctx) => {
    refresh(ctx.cwd);
  });

  pi.on("before_agent_start", () => {
    if (!pendingRestoration) return;
    const content = pendingRestoration;
    pendingRestoration = null;
    return { message: restorationMessage(content) };
  });

  pi.on("session_compact", (_event, ctx) => {
    refresh(ctx.cwd);
    if (!pendingRestoration) return;
    pi.sendMessage(restorationMessage(pendingRestoration), { triggerTurn: false });
    pendingRestoration = null;
  });

  pi.on("session_tree", (_event, ctx) => {
    refresh(ctx.cwd);
  });
}
