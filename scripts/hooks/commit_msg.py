#!/usr/bin/env python3
"""
commit-msg hook - Validates conventional commit format.

This hook validates that commit messages follow the Conventional Commits
specification: https://www.conventionalcommits.org/

Valid formats:
  type: description
  type(scope): description
  type!: breaking change description
  type(scope)!: breaking change description

Valid types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

Cross-platform compatible (Windows, macOS, Linux).
"""

import re
import sys
from pathlib import Path


# Exit codes for clarity and maintainability
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

# Valid commit types per Conventional Commits specification
VALID_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
]

# Pattern for conventional commit format
# type: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
# optional scope in parentheses
# optional ! for breaking changes
# colon and space
# description
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(" + "|".join(VALID_TYPES) + r")(\([a-zA-Z0-9_-]+\))?!?: .+"
)


def extract_subject(commit_message: str) -> str:
    """
    Extract the subject portion of a commit message.

    The subject is everything after 'type(scope): ' or 'type: '.

    Args:
        commit_message: Full commit message

    Returns:
        Subject portion of the message
    """
    # Split on first ': ' occurrence
    parts = commit_message.split(": ", 1)
    if len(parts) == 2:
        return parts[1].strip()
    return ""


def validate_subject_case(subject: str) -> tuple[bool, str]:
    """
    Validate that subject starts with lowercase letter.

    Matches commitlint rule: subject-case: [2, 'always', 'lower-case']

    Args:
        subject: The subject portion of commit message (after type/scope)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not subject:
        return False, "Subject is empty"

    first_char = subject[0]

    # Allow non-alphabetic first characters (numbers, special chars)
    if not first_char.isalpha():
        return True, ""

    # First alphabetic character must be lowercase
    if first_char.isupper():
        return False, f"subject must start with lowercase letter (found '{first_char}')"

    return True, ""


def validate_commit_message(commit_msg_file: Path) -> bool:
    """
    Validate that the commit message follows Conventional Commits format.

    Args:
        commit_msg_file: Path to the file containing the commit message

    Returns:
        True if valid, False otherwise
    """
    try:
        commit_msg = commit_msg_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"ERROR: Could not read commit message file: {e}", file=sys.stderr)
        return False

    # Get first line (subject)
    first_line = commit_msg.split("\n")[0].strip()

    if not first_line:
        print_error_message("", "Commit message is empty")
        return False

    if not CONVENTIONAL_COMMIT_PATTERN.match(first_line):
        print_error_message(first_line, "Does not follow Conventional Commits format")
        return False

    # Validate subject case (must start with lowercase)
    subject = extract_subject(first_line)
    is_valid, error_msg = validate_subject_case(subject)

    if not is_valid:
        print("")
        print(f"❌ COMMIT REJECTED - {error_msg}")
        print("")
        print("Your commit message:")
        print(f"  {first_line}")
        print("")
        print(
            "The subject must start with a lowercase letter to match CI/CD requirements."
        )
        print("")
        print("Examples:")
        print("  ✅ feat: add user authentication")
        print("  ✅ fix: resolve timeout issue")
        print("  ❌ feat: Add user authentication  (uppercase 'A')")
        print("  ❌ fix: Resolve timeout issue     (uppercase 'R')")
        print("")
        return False

    return True


def print_error_message(commit_msg: str, reason: str) -> None:
    """Print a helpful error message for invalid commit messages."""
    print("")
    print("ERROR: Commit message does not follow Conventional Commits format.")
    print("")
    print("Your commit message:")
    print(f"  {commit_msg}")
    print("")
    print("Expected format:")
    print("  type(scope): description")
    print("")
    print(f"Valid types: {', '.join(VALID_TYPES)}")
    print("")
    print("Examples:")
    print("  feat: add user dashboard")
    print("  fix(auth): resolve login timeout")
    print("  feat!: redesign API endpoints (breaking change)")
    print("  refactor(api)!: remove deprecated endpoints")
    print("")
    print("See: https://www.conventionalcommits.org/")
    print("")


def main() -> int:
    """
    Main entry point for commit-msg hook.

    Returns:
        EXIT_SUCCESS (0) on success, EXIT_FAILURE (1) on failure
    """
    if len(sys.argv) < 2:
        print("ERROR: No commit message file provided", file=sys.stderr)
        return EXIT_FAILURE

    commit_msg_file = Path(sys.argv[1])

    if not commit_msg_file.exists():
        print(
            f"ERROR: Commit message file not found: {commit_msg_file}", file=sys.stderr
        )
        return EXIT_FAILURE

    if validate_commit_message(commit_msg_file):
        return EXIT_SUCCESS
    return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
