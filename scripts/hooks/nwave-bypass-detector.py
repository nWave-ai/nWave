#!/usr/bin/env python3
"""nWave Bypass Detector - Post-commit hook."""

import os
import sys
from pathlib import Path


def main():
    """Log commit for audit purposes using DES audit logger."""
    try:
        # Add src to path to import DES modules
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        # Import DES config and audit logger
        from src.des.adapters.driven.config.des_config import DESConfig
        from src.des.adapters.driven.logging.audit_logger import log_audit_event

        # Check if audit logging is enabled
        config = DESConfig()
        if not config.audit_logging_enabled:
            return 0

        # Get commit info
        import subprocess

        result = subprocess.run(
            ["git", "log", "-1", "--format=%H|%s|%an"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            parts = result.stdout.strip().split("|", 2)
            if len(parts) >= 3:
                commit_hash, subject, author = parts
            else:
                commit_hash = parts[0] if parts else "unknown"
                subject = parts[1] if len(parts) > 1 else "unknown"
                author = "unknown"

            # Log to DES audit log
            log_audit_event(
                event_type="GIT_COMMIT",
                commit=commit_hash[:8],
                commit_full=commit_hash,
                subject=subject,
                author=author,
                no_verify=os.environ.get("PRE_COMMIT_ALLOW_NO_CONFIG", "") == "1",
            )

        return 0

    except Exception:
        # Never block on audit failures
        return 0


if __name__ == "__main__":
    sys.exit(main())
