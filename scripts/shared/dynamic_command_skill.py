"""Project the private dynamic command into a host command-skill.

The ONE source is ``nWave/tasks/nw/dynamic.md``; the catalog marks the
command ``public: false``, so nothing in the repository tree, the plugin
build, the wheel or the strip ever sees a rendered copy. This module
materializes the rendered skill only inside a DEV-mode skills install,
into a caller-owned staging directory outside the repository, and the
callers pass ``dev_mode=False`` nowhere else. A non-dev install both
materializes nothing and purges a staging leftover a previous dev
install may have left in the same host home.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts.shared.skill_distribution import SkillEntry


DYNAMIC_SKILL_NAME = "nw-dynamic"
_TASK_RELATIVE = Path("tasks") / "nw" / "dynamic.md"


def _frontmatter_value(head: str, key: str) -> str:
    """Return the first line's value for *key* in a frontmatter block.

    Folded YAML scalars (a top-level ``key:`` line continued by indented
    lines) are joined with single spaces, mirroring YAML's folded plain
    scalar semantics for this simple two-key frontmatter.
    """
    lines = head.split("\n")
    joined: list[str] = []
    for index, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            joined.append(line[len(key) + 1 :].strip())
            for continuation in lines[index + 1 :]:
                if continuation.startswith((" ", "\t")):
                    joined.append(continuation.strip())
                else:
                    break
            break
    value = " ".join(part for part in joined if part)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value


def _single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def render_dynamic_command_skill(task_text: str) -> str:
    """Render the command-skill text from the task file text (pure).

    The frontmatter carries the skill name, the task description and
    argument hint, and ``user-invocable: true``; the body is the task
    body verbatim, so the task file stays the single source. A task file
    without frontmatter is a broken tree: refuse with a reason.
    """
    if not task_text.startswith("---"):
        raise ValueError("dynamic task file has no frontmatter")
    end = task_text.find("\n---", 3)
    if end == -1:
        raise ValueError("dynamic task file frontmatter is unterminated")
    head = task_text[:end]
    body = task_text[end + 4 :]
    description = _frontmatter_value(head, "description")
    if not description:
        raise ValueError("dynamic task file frontmatter has no description")
    argument_hint = _frontmatter_value(head, "argument-hint")
    lines = [
        "---",
        "name: nw-dynamic",
        f"description: {_single_quoted(description)}",
        "user-invocable: true",
    ]
    if argument_hint:
        lines.append(f"argument-hint: {_single_quoted(argument_hint)}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def dynamic_skill_entry(
    dev_mode: bool, nwave_dir: Path, staging_dir: Path
) -> SkillEntry | None:
    """Materialize the nw-dynamic command-skill for a dev skills install.

    Reads the task file, renders the skill, writes it under
    *staging_dir*/nw-dynamic/SKILL.md and returns the entry the caller
    copies like any enumerated skill. Returns None when *dev_mode* is
    False or the task file is absent; either way a leftover staging dir
    from an earlier dev install in the same home is purged first, so a
    non-dev install never keeps a private rendered copy. The staging dir
    lives in the caller's host home, never in the repository tree.
    """
    shutil.rmtree(staging_dir, ignore_errors=True)
    if not dev_mode:
        return None
    task_file = nwave_dir / _TASK_RELATIVE
    if not task_file.is_file():
        return None
    staged = staging_dir / DYNAMIC_SKILL_NAME
    staged.mkdir(parents=True)
    (staged / "SKILL.md").write_text(
        render_dynamic_command_skill(task_file.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    return SkillEntry(name=DYNAMIC_SKILL_NAME, source_path=staged)
