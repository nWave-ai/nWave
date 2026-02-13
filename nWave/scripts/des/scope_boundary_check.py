#!/usr/bin/env python3
"""Pre-commit hook: Validate scope boundaries."""

import sys
from pathlib import Path


def main():
    """Validate scope boundaries for staged files."""
    try:
        sys.path.insert(0, str(Path.home() / ".claude" / "lib" / "python"))
        from des.validation import ScopeValidator

        validator = ScopeValidator(project_root=Path.cwd())
        result = validator.validate_git_staged_files()

        if not result.is_valid:
            print("❌ ERROR: Scope violations detected:")
            for violation in result.violations:
                print(f"  - {violation.file}: {violation.reason}")
            print("\nResolution:")
            print("  1. Update roadmap.yaml to include new scope")
            print("  2. Or unstage files outside scope")
            return 1

        print("✓ All staged files within declared scope")
        return 0
    except ImportError:
        print("⚠️  DES module not available - scope boundary check skipped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
