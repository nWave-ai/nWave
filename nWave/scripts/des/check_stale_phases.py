#!/usr/bin/env python3
"""Pre-commit hook: Detect abandoned IN_PROGRESS phases."""

import sys
from pathlib import Path


def main():
    """Check for stale IN_PROGRESS phases."""
    try:
        sys.path.insert(0, str(Path.home() / ".claude" / "lib" / "python"))
        from des.application import StaleExecutionDetector

        detector = StaleExecutionDetector(project_root=Path.cwd())
        result = detector.scan_for_stale_executions()

        if result.is_blocked:
            print("❌ ERROR: Stale IN_PROGRESS phases detected:")
            for stale in result.stale_executions:
                print(f"  - {stale.step_file}: {stale.phase_name}")
            print("\nResolution:")
            print("  1. Complete or mark phases as FAILED")
            print("  2. Or remove execution-log.yaml if workflow abandoned")
            return 1

        print("✓ No stale phases detected")
        return 0
    except ImportError:
        print("⚠️  DES module not available - stale phase check skipped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
