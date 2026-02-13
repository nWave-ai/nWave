#!/usr/bin/env python3
"""
Agent Name Synchronization Script

This script ensures agent filenames match the canonical names defined in framework-catalog.yaml.
The catalog is the SOURCE OF TRUTH for agent naming.

Usage:
    python scripts/framework/sync_agent_names.py           # Show mismatches
    python scripts/framework/sync_agent_names.py --fix     # Rename files to match catalog
    python scripts/framework/sync_agent_names.py --verify  # Exit with error code if mismatches exist (for CI)

Exit Codes:
    0 - All agent names in sync
    1 - Mismatches found (--verify mode) or errors occurred
"""

import argparse
import sys
from pathlib import Path

import yaml


def load_catalog_agents(catalog_path: Path) -> dict[str, dict]:
    """
    Load agent definitions from framework-catalog.yaml.

    Returns:
        Dict mapping canonical agent names (with underscores) to their metadata
    """
    with open(catalog_path, encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    agents = catalog.get("agents", {})
    print(f"✓ Loaded {len(agents)} agents from catalog")
    return agents


def expected_filename(canonical_name: str) -> str:
    """
    Convert canonical agent name to expected filename.

    Strategy: Keep underscores as-is for now (catalog is source of truth).
    Later we can decide: underscores vs hyphens.

    Args:
        canonical_name: Agent name from catalog (e.g., 'business_analyst')

    Returns:
        Expected filename (e.g., 'business_analyst.md')
    """
    return f"{canonical_name}.md"


def scan_agent_files(agents_dir: Path) -> list[Path]:
    """
    Scan nWave/agents/ directory for all .md files.

    Returns:
        List of Path objects for agent files (excluding reviewer agents)
    """
    agent_files = [
        f for f in agents_dir.glob("*.md") if not f.stem.endswith("-reviewer")
    ]
    print(f"✓ Found {len(agent_files)} primary agent files")
    return agent_files


def find_mismatches(
    catalog_agents: dict[str, dict], agents_dir: Path
) -> list[tuple[str, Path, str]]:
    """
    Find agent files that don't match canonical names.

    Returns:
        List of (canonical_name, current_file_path, expected_filename) tuples
    """
    mismatches = []
    existing_files = {f.name: f for f in scan_agent_files(agents_dir)}

    for canonical_name in catalog_agents:
        expected_file = expected_filename(canonical_name)

        if expected_file not in existing_files:
            # Try to find file with similar name (e.g., hyphens instead of underscores)
            similar_name = canonical_name.replace("_", "-") + ".md"
            if similar_name in existing_files:
                mismatches.append(
                    (canonical_name, existing_files[similar_name], expected_file)
                )
            else:
                print(f"⚠ WARNING: No file found for agent '{canonical_name}'")
                print(f"  Expected: {expected_file}")
                print(f"  Also tried: {similar_name}")

    return mismatches


def rename_agent_files(
    mismatches: list[tuple[str, Path, str]], agents_dir: Path
) -> int:
    """
    Rename agent files to match canonical names.

    Also renames corresponding reviewer agent files.

    Returns:
        Number of files renamed
    """
    renamed_count = 0

    for _canonical_name, current_path, expected_filename in mismatches:
        new_path = agents_dir / expected_filename
        reviewer_current = agents_dir / f"{current_path.stem}-reviewer.md"
        reviewer_new = agents_dir / f"{Path(expected_filename).stem}-reviewer.md"

        print(f"\n📝 Renaming: {current_path.name} → {expected_filename}")
        current_path.rename(new_path)
        renamed_count += 1

        # Also rename reviewer agent if it exists
        if reviewer_current.exists():
            print(f"   + Reviewer: {reviewer_current.name} → {reviewer_new.name}")
            reviewer_current.rename(reviewer_new)
            renamed_count += 1

    return renamed_count


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize agent filenames with framework-catalog.yaml"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Rename agent files to match canonical names"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Exit with error code if mismatches exist (for CI/CD)",
    )
    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).parent.parent.parent
    catalog_path = project_root / "nWave" / "framework-catalog.yaml"
    agents_dir = project_root / "nWave" / "agents"

    # Validate paths
    if not catalog_path.exists():
        print(f"❌ ERROR: Catalog not found: {catalog_path}")
        sys.exit(1)

    if not agents_dir.exists():
        print(f"❌ ERROR: Agents directory not found: {agents_dir}")
        sys.exit(1)

    print("=" * 70)
    print(" Agent Name Synchronization")
    print("=" * 70)
    print(f"Catalog (source of truth): {catalog_path.relative_to(project_root)}")
    print(f"Agents directory: {agents_dir.relative_to(project_root)}")
    print()

    # Load catalog
    try:
        catalog_agents = load_catalog_agents(catalog_path)
    except Exception as e:
        print(f"❌ ERROR loading catalog: {e}")
        sys.exit(1)

    # Find mismatches
    mismatches = find_mismatches(catalog_agents, agents_dir)

    if not mismatches:
        print("\n✅ All agent filenames match canonical names from catalog")
        sys.exit(0)

    # Report mismatches
    print(f"\n⚠  Found {len(mismatches)} filename mismatches:")
    print()
    for canonical_name, current_path, expected_filename in mismatches:
        print(f"  Canonical name: {canonical_name}")
        print(f"  Current file:   {current_path.name}")
        print(f"  Expected file:  {expected_filename}")
        print()

    # Handle modes
    if args.verify:
        print("❌ VERIFICATION FAILED: Mismatches found (use --fix to correct)")
        sys.exit(1)

    if args.fix:
        print("🔧 Renaming files to match catalog...")
        renamed = rename_agent_files(mismatches, agents_dir)
        print(f"\n✅ Renamed {renamed} files successfully")
        print("\n⚠  NOTE: You may need to update documentation references")
        sys.exit(0)

    # Default: just show mismatches
    print("Run with --fix to rename files, or --verify for CI/CD validation")
    sys.exit(1)


if __name__ == "__main__":
    main()
