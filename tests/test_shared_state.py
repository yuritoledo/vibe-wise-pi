"""Shared onboarding must not share worktree decisions or reset user preferences."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("shared_hook", ROOT / "hooks/session_start.py")
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)
spec = importlib.util.spec_from_file_location("shared_reset", ROOT / "skills/reset/reset.py")
reset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reset)


class SharedStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = self.root / "config"
        env = patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.config)})
        env.start()
        self.addCleanup(env.stop)
        self.repo = self.root / "repository"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-qm", "init"], check=True)
        self.worktree = self.root / "worktree"
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-qb", "topic", str(self.worktree)], check=True)
        common = (self.repo / ".git").resolve()
        key = hashlib.sha256(str(common).encode()).hexdigest()
        self.shared = self.config / "vibe-wise"
        self.project = self.shared / "projects" / key
        self.project.mkdir(parents=True)
        self.profile = self.shared / "profile.md"
        self.profile.write_text("# Learner Profile\nOnboarding: complete\nOverall programming: Advanced\n")
        (self.project / "project.md").write_text("Learning mode: active\nOnboarding: complete\nStack familiarity: Advanced\n")
        (self.project / "project-map.md").write_text("# Project Map\nVerified project knowledge\n")

    def context(self, cwd):
        result = hook.restore({"hook_event_name": "SessionStart", "cwd": str(cwd)})
        return result["hookSpecificOutput"]["additionalContext"] if result else ""

    def test_worktrees_reuse_profile_and_map_but_have_separate_progress(self):
        for cwd in (self.repo, self.worktree):
            local = cwd / ".vibe-wise"
            local.mkdir()
            (local / "progress.md").write_text("## Pending decision\nOnly this worktree\n")
            context = self.context(cwd)
            self.assertIn(str(self.profile), context)
            self.assertIn(str(self.project / "project-map.md"), context)
            self.assertIn(str(local / "progress.md"), context)
            other = self.repo if cwd == self.worktree else self.worktree
            self.assertNotIn(str(other / ".vibe-wise/progress.md"), context)
            self.assertIn("Reuse completed onboarding", context)

    def test_project_pause_blocks_all_worktrees(self):
        (self.project / "project.md").write_text("Learning mode: paused\nOnboarding: complete\n")
        self.assertEqual(self.context(self.repo), "")
        self.assertEqual(self.context(self.worktree), "")

    def test_global_profile_does_not_activate_unrelated_project(self):
        other = self.root / "other"
        subprocess.run(["git", "init", "-q", str(other)], check=True)
        self.assertEqual(self.context(other), "")

    def test_reset_keeps_global_profile_and_other_worktree_progress(self):
        for cwd in (self.repo, self.worktree):
            local = cwd / ".vibe-wise"
            local.mkdir()
            (local / "progress.md").write_text("## Pending decision\nAwaiting implementation approval\n")
        before = self.profile.read_bytes()
        other = (self.repo / ".vibe-wise/progress.md").read_bytes()
        preview = reset.reset(self.worktree)
        self.assertEqual(preview["status"], "preview")
        self.assertNotIn("profile.md", preview["targets"])
        self.assertEqual(preview["targets"]["project.md"], str(self.project / "project.md"))
        result = reset.reset(self.worktree, preview["confirmation"])
        self.assertEqual(result["status"], "reset")
        self.assertIn("Onboarding: incomplete", (self.project / "project.md").read_text())
        self.assertNotIn("Verified project knowledge", (self.project / "project-map.md").read_text())
        self.assertEqual(self.profile.read_bytes(), before)
        self.assertEqual((self.repo / ".vibe-wise/progress.md").read_bytes(), other)
        self.assertNotIn("Pending decision", (self.worktree / ".vibe-wise/progress.md").read_text())

    def test_symlinked_shared_project_is_not_read(self):
        outside = self.root / "outside"
        self.project.rename(outside)
        self.project.symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.context(self.worktree), "")

    def test_fresh_worktree_restores_without_creating_files(self):
        context = self.context(self.worktree)
        self.assertIn(str(self.project / "project.md"), context)
        self.assertFalse((self.worktree / ".vibe-wise").exists())

    def test_nested_directory_uses_same_project_and_worktree_progress(self):
        nested = self.worktree / "src" / "feature"
        nested.mkdir(parents=True)
        self.assertEqual(self.context(nested), self.context(self.worktree))

    def test_clone_does_not_reuse_project_activation(self):
        clone = self.root / "clone"
        subprocess.run(["git", "clone", "-q", str(self.repo), str(clone)], check=True)
        self.assertEqual(self.context(clone), "")

    def test_git_environment_cannot_select_another_project(self):
        with patch.dict(os.environ, {"GIT_DIR": str(self.root / "wrong"), "GIT_WORK_TREE": str(self.root)}):
            self.assertIn(str(self.project / "project.md"), self.context(self.worktree))

    def test_reset_rejects_changed_shared_notes(self):
        preview = reset.reset(self.worktree)
        (self.project / "project-map.md").write_text("Updated by another session\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            reset.reset(self.worktree, preview["confirmation"])
        self.assertFalse((self.worktree / ".vibe-wise").exists())

    def test_reset_stages_each_replacement_next_to_its_target(self):
        # Shared config and a checkout may live on different filesystems.
        replace = os.replace

        def same_filesystem_replace(source, destination):
            self.assertEqual(Path(source).parent, Path(destination).parent)
            return replace(source, destination)

        preview = reset.reset(self.worktree)
        self.assertFalse((self.worktree / ".vibe-wise").exists())
        with patch.object(reset.os, "replace", side_effect=same_filesystem_replace):
            result = reset.reset(self.worktree, preview["confirmation"])
        backup = Path(result["backup"])
        self.assertIn("Stack familiarity: Advanced", (backup / "project.md").read_text())
        self.assertIn("Verified project knowledge", (backup / "project-map.md").read_text())
        self.assertFalse((backup / "profile.md").exists())
        manifest = json.loads((backup / "targets.json").read_text())
        self.assertEqual(manifest, preview["targets"])
        self.assertFalse(list(self.project.glob(".reset-*")))

    def test_legacy_local_profile_takes_precedence_without_migration(self):
        local = self.worktree / ".vibe-wise"
        local.mkdir()
        (local / "profile.md").write_text("Learning mode: paused\nOnboarding: complete\n")
        self.assertEqual(self.context(self.worktree), "")
        self.assertTrue((local / "profile.md").is_file())


if __name__ == "__main__":
    unittest.main()
