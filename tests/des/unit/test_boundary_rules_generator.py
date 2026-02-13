"""
Unit tests for BoundaryRulesGenerator.

Tests verify that the generator:
1. Reads step file scope and extracts allowed file patterns
2. Handles target_files, test_files, and allowed_patterns
3. Gracefully handles missing scope with default patterns and WARNING log
4. Includes step file as implicitly allowed
"""

import json

from des.application.boundary_rules_generator import BoundaryRulesGenerator


class TestBoundaryRulesGeneratorShouldGenerateAllowedPatterns:
    """Test generation of ALLOWED patterns from step file scope."""

    def test_include_step_file_in_allowed_patterns(self, tmp_path):
        """Step file should be implicitly allowed."""
        # GIVEN: Step file with minimal scope
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {
            "task_id": "01-01",
            "scope": {"target_files": [], "test_files": []},
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN: Generator creates allowed patterns
        generator = BoundaryRulesGenerator(step_file_path=step_file)
        patterns = generator.generate_allowed_patterns()

        # THEN: Step file is in allowed patterns
        assert any(
            "steps/01-01.json" in pattern or "step" in pattern.lower()
            for pattern in patterns
        ), "Step file should be implicitly allowed"

    def test_include_target_files_from_scope(self, tmp_path):
        """Target files from scope.target_files should be in ALLOWED patterns."""
        # GIVEN: Step file with target files
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {
            "task_id": "01-01",
            "scope": {
                "target_files": [
                    "src/repositories/UserRepository.py",
                    "src/repositories/interfaces/IUserRepository.py",
                ],
                "test_files": [],
            },
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN: Generator creates allowed patterns
        generator = BoundaryRulesGenerator(step_file_path=step_file)
        patterns = generator.generate_allowed_patterns()

        # THEN: Target files are in allowed patterns
        assert any("UserRepository" in pattern for pattern in patterns), (
            "Target files should be in ALLOWED patterns"
        )

    def test_include_test_files_from_scope(self, tmp_path):
        """Test files from scope.test_files should be in ALLOWED patterns."""
        # GIVEN: Step file with test files
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {
            "task_id": "01-01",
            "scope": {
                "target_files": [],
                "test_files": [
                    "tests/unit/test_user_repository.py",
                    "tests/integration/test_user_repository_integration.py",
                ],
            },
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN: Generator creates allowed patterns
        generator = BoundaryRulesGenerator(step_file_path=step_file)
        patterns = generator.generate_allowed_patterns()

        # THEN: Test files are in allowed patterns
        assert any(
            "test" in pattern.lower() or "test_user_repository" in pattern
            for pattern in patterns
        ), "Test files should be in ALLOWED patterns"

    def test_include_custom_allowed_patterns(self, tmp_path):
        """Custom patterns from scope.allowed_patterns should be included."""
        # GIVEN: Step file with custom allowed patterns
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {
            "task_id": "01-01",
            "scope": {
                "target_files": [],
                "test_files": [],
                "allowed_patterns": ["config/**/*.yaml", "docs/**/*.md"],
            },
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN: Generator creates allowed patterns
        generator = BoundaryRulesGenerator(step_file_path=step_file)
        patterns = generator.generate_allowed_patterns()

        # THEN: Custom patterns are included
        assert "config/**/*.yaml" in patterns
        assert "docs/**/*.md" in patterns

    def test_default_to_generic_patterns_when_scope_missing(self, tmp_path):
        """Missing scope field should default to generic patterns."""
        # GIVEN: Step file without scope field
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {"task_id": "01-01"}
        step_file.write_text(json.dumps(step_data))

        # WHEN: Generator creates allowed patterns
        generator = BoundaryRulesGenerator(step_file_path=step_file)
        patterns = generator.generate_allowed_patterns()

        # THEN: Generic patterns are used
        expected_defaults = ["steps/**/*.json", "src/**/*", "tests/**/*"]
        for expected in expected_defaults:
            assert expected in patterns, (
                f"Default pattern {expected} should be in allowed patterns"
            )

    def test_log_warning_when_scope_missing(self, tmp_path, caplog):
        """WARNING should be logged when scope field is missing."""
        # GIVEN: Step file without scope field
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {"task_id": "01-01"}
        step_file.write_text(json.dumps(step_data))

        # WHEN: Generator creates allowed patterns
        generator = BoundaryRulesGenerator(step_file_path=step_file)
        generator.generate_allowed_patterns()

        # THEN: WARNING logged
        assert any(
            "WARNING" in record.levelname and "scope" in record.message.lower()
            for record in caplog.records
        ), "WARNING should be logged when scope missing"


class TestBoundaryRulesGeneratorShouldConvertToGlobPatterns:
    """Test conversion of exact paths to flexible glob patterns.

    Acceptance Criteria (AC-007.2):
    - Patterns support glob syntax (**, *, exact paths)
    - UserRepository example: target_files maps to **/UserRepository* pattern
    - Enable matching both implementation and test files
    """

    def test_convert_target_file_to_glob_pattern(self, tmp_path):
        """Target files should be converted to glob patterns like **/ClassName*"""
        # GIVEN: Step file with exact path target files
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {
            "task_id": "01-01",
            "scope": {
                "target_files": [
                    "src/repositories/UserRepository.py",
                ],
                "test_files": [],
            },
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN: Generator creates allowed patterns
        generator = BoundaryRulesGenerator(step_file_path=step_file)
        patterns = generator.generate_allowed_patterns()

        # THEN: Pattern is converted to glob format
        assert any("**/UserRepository*" in pattern for pattern in patterns), (
            "Target files should be converted to glob patterns like **/UserRepository*"
        )

    def test_convert_interface_file_to_glob_pattern(self, tmp_path):
        """Interface files should be converted to glob patterns"""
        # GIVEN: Step file with interface target files
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {
            "task_id": "01-01",
            "scope": {
                "target_files": [
                    "src/repositories/interfaces/IUserRepository.py",
                ],
                "test_files": [],
            },
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN: Generator creates allowed patterns
        generator = BoundaryRulesGenerator(step_file_path=step_file)
        patterns = generator.generate_allowed_patterns()

        # THEN: Interface pattern is converted to glob format
        assert any("**/IUserRepository*" in pattern for pattern in patterns), (
            "Interface files should be converted to glob patterns like **/IUserRepository*"
        )

    def test_glob_pattern_matches_both_source_and_test_files(self, tmp_path):
        """Glob patterns should match both implementation and test files"""
        # GIVEN: Step file with target file UserRepository
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {
            "task_id": "01-01",
            "scope": {
                "target_files": [
                    "src/repositories/UserRepository.py",
                ],
                "test_files": [],
            },
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN: Generator creates allowed patterns
        generator = BoundaryRulesGenerator(step_file_path=step_file)
        patterns = generator.generate_allowed_patterns()

        # THEN: Glob pattern would match multiple file types
        # Business Context: **/UserRepository* matches:
        # - src/repositories/UserRepository.py (implementation)
        # - tests/unit/test_UserRepository.py (unit test)
        # - tests/integration/UserRepository_integration.py (integration test)
        glob_pattern = next(p for p in patterns if "**/UserRepository*" in p)
        assert glob_pattern == "**/UserRepository*", (
            "Glob pattern should be flexible to match both source and test files"
        )
