"""Regression for public issue #90: public projections keep repository dotfiles."""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = (
    REPO_ROOT / ".github/workflows/release-prod.yml",
    REPO_ROOT / ".github/workflows/release-rc.yml",
)
BASE_REVISION = "094f7359310e71993deb5fbbd214647a46847ee8"
BASE_GITIGNORE_SHA256 = (
    "4223e4f34b60b18f278ce28dc8db1150072f39524b659114b38ce640e3f8ec97"
)
BASE_WORKFLOW_SHA256 = {
    "release-prod.yml": (
        "218d62b410885e079283024e0dea2434db0fb6310508bd349256a5ab7d36eb18"
    ),
    "release-rc.yml": (
        "4bc5ee5905a64bf16573f05a6c3aa5ba3eb0264a04e2b50b5f162afae741cfa9"
    ),
}


def _sync_filters(workflow: Path) -> list[str]:
    """Read the first source-to-public-target rsync filter list from a workflow."""
    lines = workflow.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if "rsync -avL --delete" in line)
    filters: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip().removesuffix("\\").strip()
        if stripped.startswith("source/ "):
            break
        filters.extend(shlex.split(stripped))
    return filters


class PublicSyncDotfilesTest(unittest.TestCase):
    def test_issue_90_projection_and_ignore_policy(self) -> None:
        def isolated_git_environment(root_path: Path) -> dict[str, str]:
            isolated_home = root_path / "home"
            global_config = root_path / "global.gitconfig"
            system_config = root_path / "system.gitconfig"
            isolated_home.mkdir()
            (isolated_home / ".config").mkdir()
            global_config.touch()
            system_config.touch()
            environment = {
                key: os.environ[key]
                for key in ("PATH", "LANG", "LC_ALL", "TZ")
                if key in os.environ
            }
            environment.update(
                {
                    "HOME": str(isolated_home),
                    "XDG_CONFIG_HOME": str(isolated_home / ".config"),
                    "GIT_CONFIG_GLOBAL": str(global_config),
                    "GIT_CONFIG_SYSTEM": str(system_config),
                    "GIT_CONFIG_NOSYSTEM": "1",
                }
            )
            self.assertNotIn("GIT_CONFIG_COUNT", environment)
            self.assertFalse(
                any(
                    key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))
                    for key in environment
                )
            )
            self.assertFalse(
                {
                    "GIT_DIR",
                    "GIT_WORK_TREE",
                    "GIT_INDEX_FILE",
                    "GIT_OBJECT_DIRECTORY",
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                }
                & environment.keys()
            )
            return environment

        required_ignored_paths = (
            "tsunami/private-state",
            ".tsunami/private-state",
            ".mcp.json",
            ".claude/settings.local.json",
            "CLAUDE.local.md",
            "pkg/__pycache__/sentinel.txt",
            "module.pyc",
            "dist/package.whl",
            "build/generated.o",
        )
        owner_failures: list[str] = []
        expected_gitattributes = (REPO_ROOT / ".gitattributes").read_bytes()
        policy_failures: list[str] = []
        policy_passes: list[str] = []

        self.assertIsNotNone(shutil.which("rsync"), "rsync is required")
        self.assertIsNotNone(shutil.which("git"), "git is required")

        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            git_env = isolated_git_environment(root_path)
            base_gitignore = subprocess.run(
                [
                    "git",
                    "-C",
                    str(REPO_ROOT),
                    "show",
                    f"{BASE_REVISION}:.gitignore",
                ],
                check=True,
                capture_output=True,
                env=git_env,
            ).stdout
            self.assertEqual(
                hashlib.sha256(base_gitignore).hexdigest(), BASE_GITIGNORE_SHA256
            )
            marker = b"tsunami/\n"
            self.assertEqual(base_gitignore.count(marker), 1)
            expected_gitignore = base_gitignore.replace(
                marker, marker + b".tsunami/\n", 1
            )
            candidate_gitignore = (REPO_ROOT / ".gitignore").read_bytes()
            if candidate_gitignore != expected_gitignore:
                owner_failures.append(
                    ".gitignore:actual-sha256="
                    f"{hashlib.sha256(candidate_gitignore).hexdigest()},"
                    "expected-authorized-sha256="
                    f"{hashlib.sha256(expected_gitignore).hexdigest()}"
                )

            probe_target = root_path / "config-injection-probe"
            subprocess.run(
                ["git", "init", "--quiet", str(probe_target)],
                check=True,
                capture_output=True,
                text=True,
                env=git_env,
            )
            (probe_target / ".gitignore").write_bytes(base_gitignore)
            probe_sentinel = probe_target / ".tsunami/private-state"
            probe_sentinel.parent.mkdir(parents=True)
            probe_sentinel.write_text("private\n", encoding="utf-8")
            injected_excludes = root_path / "injected-excludes"
            injected_excludes.write_text(".tsunami/\n", encoding="utf-8")
            poisoned_env = {
                **git_env,
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.excludesFile",
                "GIT_CONFIG_VALUE_0": str(injected_excludes),
            }
            poisoned_check = subprocess.run(
                [
                    "git",
                    "-C",
                    str(probe_target),
                    "check-ignore",
                    "--quiet",
                    "--",
                    ".tsunami/private-state",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=poisoned_env,
            )
            neutral_check = subprocess.run(
                [
                    "git",
                    "-C",
                    str(probe_target),
                    "check-ignore",
                    "--quiet",
                    "--",
                    ".tsunami/private-state",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=git_env,
            )
            self.assertEqual(poisoned_check.returncode, 0)
            self.assertEqual(neutral_check.returncode, 1)

        for workflow in WORKFLOWS:
            self.assertEqual(
                hashlib.sha256(workflow.read_bytes()).hexdigest(),
                BASE_WORKFLOW_SHA256[workflow.name],
                f"unauthorized workflow owner change: {workflow}",
            )

        for workflow in WORKFLOWS:
            with (
                self.subTest(workflow=workflow.name),
                tempfile.TemporaryDirectory() as root,
            ):
                root_path = Path(root)
                source = root_path / "source"
                target = root_path / "target"
                mutant_target = root_path / "mutant-target"
                git_env = isolated_git_environment(root_path)

                (source / ".git").mkdir(parents=True)
                (source / ".nwave").mkdir()
                (source / ".git/HEAD").write_text(
                    "source metadata", encoding="utf-8"
                )
                (source / ".nwave/private-state").write_text(
                    "private", encoding="utf-8"
                )
                (source / ".gitignore").write_bytes(candidate_gitignore)
                (source / ".gitattributes").write_bytes(expected_gitattributes)

                subprocess.run(
                    ["git", "init", "--quiet", str(target)],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=git_env,
                )
                target_head_before = (target / ".git/HEAD").read_bytes()
                (target / ".gitignore").write_bytes(b"stale ignore policy\n")
                (target / ".gitattributes").write_bytes(b"stale attributes\n")

                filters = _sync_filters(workflow)
                exclusions = [
                    filters[index + 1]
                    for index, item in enumerate(filters[:-1])
                    if item == "--exclude"
                ]
                self.assertIn(".git", exclusions)
                self.assertNotIn(".git*", exclusions)
                subprocess.run(
                    ["rsync", "-a", *filters, f"{source}/", f"{target}/"],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                self.assertEqual(
                    (target / ".gitignore").read_bytes(), candidate_gitignore
                )
                self.assertEqual(
                    (target / ".gitattributes").read_bytes(),
                    expected_gitattributes,
                )
                self.assertEqual(
                    (target / ".git/HEAD").read_bytes(), target_head_before
                )
                self.assertFalse((target / ".nwave").exists())

                for relative_path in required_ignored_paths:
                    sentinel = target / relative_path
                    sentinel.parent.mkdir(parents=True, exist_ok=True)
                    sentinel.write_text("private or generated\n", encoding="utf-8")
                    check_ignore = subprocess.run(
                        [
                            "git",
                            "-C",
                            str(target),
                            "check-ignore",
                            "--quiet",
                            "--",
                            relative_path,
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                        env=git_env,
                    )
                    ordinary_add = subprocess.run(
                        [
                            "git",
                            "-C",
                            str(target),
                            "add",
                            "--",
                            relative_path,
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                        env=git_env,
                    )
                    cached = subprocess.run(
                        [
                            "git",
                            "-C",
                            str(target),
                            "ls-files",
                            "--cached",
                            "--",
                            relative_path,
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        env=git_env,
                    ).stdout.splitlines()
                    observation = (
                        f"{workflow.name}:{relative_path}:"
                        f"check-ignore={check_ignore.returncode},"
                        f"add={ordinary_add.returncode},cached={cached!r}"
                    )
                    if (
                        check_ignore.returncode == 0
                        and ordinary_add.returncode != 0
                        and not cached
                    ):
                        policy_passes.append(observation)
                    else:
                        policy_failures.append(observation)

                mutant_filters = list(filters)
                replacements = 0
                for index, item in enumerate(mutant_filters[:-1]):
                    if item == "--exclude" and mutant_filters[index + 1] == ".git":
                        mutant_filters[index + 1] = ".git*"
                        replacements += 1
                self.assertEqual(replacements, 1)
                subprocess.run(
                    ["git", "init", "--quiet", str(mutant_target)],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=git_env,
                )
                mutant_head_before = (mutant_target / ".git/HEAD").read_bytes()
                subprocess.run(
                    [
                        "rsync",
                        "-a",
                        *mutant_filters,
                        f"{source}/",
                        f"{mutant_target}/",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    (mutant_target / ".git/HEAD").read_bytes(), mutant_head_before
                )
                self.assertFalse((mutant_target / ".gitignore").exists())
                self.assertFalse((mutant_target / ".gitattributes").exists())

        self.assertEqual(
            owner_failures + policy_failures,
            [],
            f"passing={policy_passes!r}; "
            f"owner-failures={owner_failures!r}; "
            f"policy-failures={policy_failures!r}",
        )

    def test_release_projection_excludes_git_metadata_not_public_dotfiles(self) -> None:
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                filters = _sync_filters(workflow)
                exclusions = [
                    filters[index + 1]
                    for index, item in enumerate(filters[:-1])
                    if item == "--exclude"
                ]

                self.assertIn(".git", exclusions)
                self.assertNotIn(".git*", exclusions)

    @unittest.skipUnless(shutil.which("rsync"), "rsync is unavailable on this runner")
    def test_release_projection_preserves_public_dotfiles_only(self) -> None:
        for workflow in WORKFLOWS:
            with (
                self.subTest(workflow=workflow.name),
                tempfile.TemporaryDirectory() as root,
            ):
                root_path = Path(root)
                source = root_path / "source"
                target = root_path / "target"
                (source / ".git").mkdir(parents=True)
                (source / ".nwave").mkdir()
                (target / ".git").mkdir(parents=True)
                (source / ".git/HEAD").write_text("source metadata", encoding="utf-8")
                (target / ".git/HEAD").write_text("target metadata", encoding="utf-8")
                (source / ".nwave/private-state").write_text(
                    "private", encoding="utf-8"
                )
                (source / ".gitignore").write_text(".nwave/\n", encoding="utf-8")
                (source / ".gitattributes").write_text(
                    "* text=auto\n", encoding="utf-8"
                )

                subprocess.run(
                    [
                        "rsync",
                        "-a",
                        *_sync_filters(workflow),
                        f"{source}/",
                        f"{target}/",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                self.assertTrue((target / ".gitignore").is_file())
                self.assertTrue((target / ".gitattributes").is_file())
                self.assertEqual(
                    (target / ".git/HEAD").read_text(encoding="utf-8"),
                    "target metadata",
                )
                self.assertFalse((target / ".nwave").exists())


if __name__ == "__main__":
    unittest.main()
