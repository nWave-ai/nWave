#!/usr/bin/env python3
"""
Documentation Freshness Check Hook

Validates that documentation is up-to-date when code changes are committed.
Fails the commit if documentation appears stale, with instructions to update.

Usage:
    python scripts/hooks/check_documentation_freshness.py

Exit codes:
    0 - Documentation is fresh or no code changes
    1 - Documentation appears stale, commit blocked
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_staged_files():
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [f.strip() for f in result.stdout.split("\n") if f.strip()]
    except subprocess.CalledProcessError:
        return []


def get_file_last_modified(filepath):
    """Get last modification time of a file."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ai", "--", filepath],
            capture_output=True,
            text=True,
            check=True,
        )
        date_str = result.stdout.strip()
        if date_str:
            return datetime.fromisoformat(date_str.replace(" +", "+"))
        return None
    except (subprocess.CalledProcessError, ValueError):
        return None


def categorize_files(files):
    """Categorize files into code, docs, and other."""
    code_files = []
    doc_files = []

    code_extensions = {".py", ".sh", ".yaml", ".yml", ".md"}
    code_patterns = ["nWave/", "scripts/", "tools/", "tests/"]
    doc_patterns = ["docs/", "README.md"]

    for f in files:
        path = Path(f)

        # Skip if file doesn't exist (deleted files)
        if not path.exists():
            continue

        # Documentation files
        if any(f.startswith(pattern) for pattern in doc_patterns):
            doc_files.append(f)
        # Code files (including agent/command definitions)
        elif any(f.startswith(pattern) for pattern in code_patterns):
            if path.suffix in code_extensions or "framework-catalog.yaml" in f:
                code_files.append(f)

    return code_files, doc_files


def check_documentation_freshness(code_files, doc_files):
    """Check if documentation needs updating based on code changes."""
    issues = []

    # Check 1: Code changes without documentation updates
    if code_files and not doc_files:
        issues.append(
            f"⚠️  {len(code_files)} code file(s) changed but no documentation updated"
        )

    # Check 2: framework-catalog.yaml changed without docs update
    if any("framework-catalog.yaml" in f for f in code_files):
        if not any("README.md" in f or "docs/" in f for f in doc_files):
            issues.append(
                "⚠️  framework-catalog.yaml changed (agents/commands) - documentation likely needs update"
            )

    # Check 3: Agent files changed
    agent_files = [f for f in code_files if "nWave/agents/" in f]
    if agent_files:
        if not any("docs/reference/" in f or "README.md" in f for f in doc_files):
            issues.append(
                f"⚠️  {len(agent_files)} agent file(s) changed - documentation likely needs update"
            )

    # Check 4: Command files changed
    command_files = [
        f for f in code_files if "nWave/tasks/nw/" in f or "nWave/commands/" in f
    ]
    if command_files:
        if not any("docs/reference/" in f or "docs/guides/" in f for f in doc_files):
            issues.append(
                f"⚠️  {len(command_files)} command file(s) changed - documentation likely needs update"
            )

    return issues


def main():
    print("Checking documentation freshness...")

    staged_files = get_staged_files()

    if not staged_files:
        print("✓ No staged files to check")
        return 0

    code_files, doc_files = categorize_files(staged_files)

    if not code_files:
        print("✓ No code changes - documentation check skipped")
        return 0

    issues = check_documentation_freshness(code_files, doc_files)

    if not issues:
        print("✓ Documentation appears current")
        return 0

    # Documentation appears stale - block commit
    print("\n" + "=" * 80)
    print("❌ COMMIT BLOCKED: Documentation may be stale")
    print("=" * 80)
    print()
    print("Issues detected:")
    for issue in issues:
        print(f"  {issue}")
    print()
    print("CODE CHANGES:")
    for f in code_files[:10]:  # Show first 10
        print(f"  • {f}")
    if len(code_files) > 10:
        print(f"  ... and {len(code_files) - 10} more")
    print()
    print("REQUIRED ACTION (for LLM):")
    print("  1. Review code changes to determine what documentation needs updating")
    print(
        '  2. Run: /nw:document "[topic-based-on-changes]" --type=[tutorial|howto|reference|explanation]'
    )
    print("  3. Examples:")
    print('     • Agent changes: /nw:document "Agent Name Updates" --type=reference')
    print('     • Command changes: /nw:document "Command Changes" --type=reference')
    print(
        '     • Framework changes: /nw:document "Framework Updates" --type=explanation'
    )
    print("  4. Add updated documentation to commit: git add docs/")
    print("  5. Retry commit")
    print()
    print("OVERRIDE (use sparingly):")
    print("  git commit --no-verify")
    print()
    print("=" * 80)

    return 1


if __name__ == "__main__":
    sys.exit(main())
