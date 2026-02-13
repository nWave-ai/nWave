"""
BoundaryRulesGenerator for scope-based file pattern generation.

This module extracts allowed file patterns from step file scope definitions,
ensuring agents can only modify files relevant to their assigned tasks.
"""

import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class BoundaryRulesGenerator:
    """
    Generate ALLOWED file patterns from step file scope.

    The generator reads step file scope field and extracts:
    - target_files: Implementation files to be modified
    - test_files: Test files for TDD workflow
    - allowed_patterns: Custom glob patterns
    - step file itself (implicitly allowed)

    If scope field is missing, defaults to generic patterns with WARNING log.
    """

    DEFAULT_PATTERNS = ["steps/**/*.json", "src/**/*", "tests/**/*"]

    def __init__(self, step_file_path: Path | str):
        """
        Initialize generator with step file path.

        Args:
            step_file_path: Path to step JSON file
        """
        self.step_file_path = Path(step_file_path)
        self._step_data = None

    def generate_allowed_patterns(self) -> list[str]:
        """
        Generate allowed file patterns from step scope.

        Returns:
            List of allowed file patterns including:
            - Step file path
            - target_files from scope (converted to glob patterns)
            - test_files from scope (converted to glob patterns)
            - allowed_patterns from scope (used as-is)
            - Default patterns if scope missing

        Pattern Conversion:
            Exact paths are converted to flexible glob patterns:
            - "src/repositories/UserRepository.py" -> "**/UserRepository*"
            - Enables matching both source and test files
            - Supports glob syntax: **, *, exact paths
        """
        self._load_step_file()

        patterns = []

        # Always include step file
        patterns.append(str(self.step_file_path))

        scope = self._step_data.get("scope")
        if not scope:
            logger.warning(
                f"Step file {self.step_file_path} missing scope field. "
                f"Using default patterns: {self.DEFAULT_PATTERNS}"
            )
            patterns.extend(self.DEFAULT_PATTERNS)
            return patterns

        # Add target files (converted to glob patterns)
        target_files = scope.get("target_files", [])
        for target_file in target_files:
            patterns.append(self._convert_to_glob_pattern(target_file))

        # Add test files (converted to glob patterns)
        test_files = scope.get("test_files", [])
        for test_file in test_files:
            patterns.append(self._convert_to_glob_pattern(test_file))

        # Add custom allowed patterns (used as-is)
        allowed_patterns = scope.get("allowed_patterns", [])
        patterns.extend(allowed_patterns)

        return patterns

    def _convert_to_glob_pattern(self, file_path: str) -> str:
        """
        Convert exact file path to flexible glob pattern.

        Extracts the class/module name from the path and creates a pattern
        that matches files with that name in any directory.

        Args:
            file_path: Exact file path like "src/repositories/UserRepository.py"

        Returns:
            Glob pattern like "**/UserRepository*"

        Examples:
            "src/repositories/UserRepository.py" -> "**/UserRepository*"
            "src/repositories/interfaces/IUserRepository.py" -> "**/IUserRepository*"
            "tests/unit/test_user_repository.py" -> "**/test_user_repository*"
        """
        # Extract filename from path
        path = Path(file_path)
        filename = path.stem  # Gets filename without extension

        # Create glob pattern
        return f"**/{filename}*"

    def _load_step_file(self) -> None:
        """Load step file JSON data."""
        if self._step_data is None:
            with open(self.step_file_path) as f:
                self._step_data = json.load(f)
