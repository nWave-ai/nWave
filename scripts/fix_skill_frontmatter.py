#!/usr/bin/env python3
"""Fix skill frontmatter: add disable-model-invocation: true and normalize names to nw- prefix.

Agent-only skills should NOT appear in the "/" slash command menu.
Setting disable-model-invocation: true hides them from users while keeping
them available to Claude and sub-agents.

Additionally, frontmatter name: fields are updated to match the
directory name (nw-prefixed) to avoid collisions in the skill registry.

Usage:
    python scripts/fix_skill_frontmatter.py          # dry-run
    python scripts/fix_skill_frontmatter.py --apply   # write changes
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def _parse_frontmatter(content: str) -> tuple[dict[str, str], int, int] | None:
    """Parse YAML frontmatter from markdown content.

    Returns (fields_dict, start_offset, end_offset) or None.
    Fields are stored as raw strings to preserve formatting.
    """
    if not content.startswith("---\n"):
        return None
    end = content.find("\n---\n", 4)
    if end == -1:
        if content.rstrip().endswith("---"):
            end = content.rstrip().rfind("---")
        else:
            return None

    block = content[4:end]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        m = re.match(r"^(\S+):\s*(.*)", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields, 4, end


def fix_skill_file(
    skill_path: Path, dir_name: str, *, apply: bool = False
) -> list[str]:
    """Fix a single skill file's frontmatter.

    Returns list of changes made (or that would be made).
    """
    content = skill_path.read_text(encoding="utf-8")
    result = _parse_frontmatter(content)
    if result is None:
        return [f"  SKIP: no frontmatter in {skill_path}"]

    fields, fm_start, fm_end = result
    fm_block = content[fm_start:fm_end]
    changes: list[str] = []
    new_block = fm_block

    # Fix 1: name should match directory name (nw-prefixed)
    current_name = fields.get("name", "")
    if current_name != dir_name:
        old_line = f"name: {current_name}"
        new_line = f"name: {dir_name}"
        if old_line in new_block:
            new_block = new_block.replace(old_line, new_line, 1)
            changes.append(f"  name: {current_name} -> {dir_name}")

    # Fix 2: add disable-model-invocation: true if not present
    if "user-invocable" not in fields:
        # Add after description line
        desc_match = re.search(r"^description:.*$", new_block, re.MULTILINE)
        if desc_match:
            insert_pos = desc_match.end()
            new_block = (
                new_block[:insert_pos]
                + "\ndisable-model-invocation: true"
                + new_block[insert_pos:]
            )
            changes.append("  + disable-model-invocation: true")
    elif fields.get("user-invocable") != "false":
        old = f"user-invocable: {fields['user-invocable']}"
        new = "disable-model-invocation: true"
        new_block = new_block.replace(old, new, 1)
        changes.append(f"  user-invocable: {fields['user-invocable']} -> false")

    if changes and apply:
        new_content = content[:fm_start] + new_block + content[fm_end:]
        skill_path.write_text(new_content, encoding="utf-8")

    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes to files")
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path("nWave/skills"),
        help="Skills source directory",
    )
    args = parser.parse_args()

    skills_dir = args.skills_dir
    if not skills_dir.exists():
        print(f"Skills directory not found: {skills_dir}")
        return

    mode = "APPLYING" if args.apply else "DRY-RUN"
    print(f"{'=' * 70}")
    print(f"  Skill Frontmatter Fixer ({mode})")
    print(f"{'=' * 70}")

    total_files = 0
    total_changes = 0
    already_ok = 0

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or not skill_dir.name.startswith("nw-"):
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        total_files += 1
        changes = fix_skill_file(skill_file, skill_dir.name, apply=args.apply)

        if changes and not all(c.startswith("  SKIP") for c in changes):
            print(f"\n  {skill_dir.name}:")
            for c in changes:
                print(f"    {c}")
            total_changes += 1
        else:
            already_ok += 1

    print(f"\n{'=' * 70}")
    print("  Summary:")
    print(f"    Files scanned:      {total_files}")
    print(f"    Already up-to-date: {already_ok}")
    print(f"    Files changed:      {total_changes}")
    if not args.apply and total_changes > 0:
        print("\n  Run with --apply to write changes.")
    elif args.apply and total_changes > 0:
        print("\n  Changes applied.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
