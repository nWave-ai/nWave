#!/usr/bin/env python3
"""
YAML File Validation Script

Validates all YAML files in the repository to catch syntax errors before CI/CD.
This script mirrors the YAML validation that GitHub Actions performs.

Usage:
    python3 scripts/validation/validate_yaml_files.py [--fix] [--verbose]

Exit codes:
    0: All YAML files are valid
    1: One or more YAML files have syntax errors
"""

import argparse
import sys
from pathlib import Path

import yaml


class YAMLValidator:
    """Validates YAML files across the repository"""

    def __init__(self, root_dir: Path, verbose: bool = False):
        self.root_dir = root_dir
        self.verbose = verbose
        self.errors = []
        self.warnings = []

    def find_yaml_files(self) -> list[Path]:
        """Find all YAML files in the repository"""
        yaml_patterns = ["**/*.yaml", "**/*.yml"]
        exclude_dirs = {
            ".git",
            "node_modules",
            ".pytest_cache",
            "__pycache__",
            "dist",
            ".mypy_cache",
            ".ruff_cache",
        }

        yaml_files = []
        for pattern in yaml_patterns:
            for file_path in self.root_dir.glob(pattern):
                # Skip excluded directories
                if any(exclude_dir in file_path.parts for exclude_dir in exclude_dirs):
                    continue
                yaml_files.append(file_path)

        return sorted(yaml_files)

    def validate_file(self, file_path: Path) -> tuple[bool, str]:
        """
        Validate a single YAML file

        Returns:
            (is_valid, error_message)
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Try to load as single document first
            try:
                yaml.safe_load(content)
                return True, ""
            except yaml.YAMLError:
                # If single document fails, try multi-document
                list(yaml.safe_load_all(content))
                return True, ""

        except yaml.YAMLError as e:
            error_msg = f"Line {e.problem_mark.line + 1}, Col {e.problem_mark.column + 1}: {e.problem}"
            if e.context:
                error_msg = f"{e.context}\n  {error_msg}"
            return False, error_msg
        except Exception as e:
            return False, f"Unexpected error: {e!s}"

    def validate_all(self) -> bool:
        """
        Validate all YAML files in the repository

        Returns:
            True if all files are valid, False otherwise
        """
        yaml_files = self.find_yaml_files()

        if self.verbose:
            print(f"Found {len(yaml_files)} YAML files to validate")
            print("=" * 70)

        all_valid = True

        for file_path in yaml_files:
            relative_path = file_path.relative_to(self.root_dir)
            is_valid, error_msg = self.validate_file(file_path)

            if is_valid:
                if self.verbose:
                    print(f"✓ {relative_path}")
            else:
                all_valid = False
                print(f"✗ {relative_path}")
                print(f"  {error_msg}")
                self.errors.append((relative_path, error_msg))

        return all_valid

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 70)
        print("YAML Validation Summary")
        print("=" * 70)

        if not self.errors:
            print("✅ All YAML files are valid")
            return

        print(f"❌ Found {len(self.errors)} YAML file(s) with errors:")
        print()
        for file_path, error_msg in self.errors:
            print(f"  {file_path}")
            print(f"    {error_msg}")
        print()
        print("Fix these errors before committing!")


def main():
    parser = argparse.ArgumentParser(description="Validate YAML files in repository")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Repository root directory"
    )

    args = parser.parse_args()

    validator = YAMLValidator(args.root, verbose=args.verbose)
    all_valid = validator.validate_all()
    validator.print_summary()

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
