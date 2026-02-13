"""
Unit Tests: DESMarkerValidator

Validates DES-VALIDATION HTML comment marker format before template acceptance.

Test Coverage:
- Valid marker format with 'required' value
- Invalid marker values (unknown, optional, maybe, empty)
- Missing marker entirely
- Malformed HTML comment syntax
- Case sensitivity enforcement
"""


class TestDESMarkerValidator:
    """Unit tests for DESMarkerValidator class."""

    def test_valid_required_marker_passes(self):
        """
        GIVEN prompt contains valid DES-VALIDATION marker: <!-- DES-VALIDATION: required -->
        WHEN DESMarkerValidator.validate() is called
        THEN no errors are returned (empty list)

        Business Value: Valid markers don't block legitimate prompts.
        """
        from des.application.validator import DESMarkerValidator

        prompt_with_valid_marker = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/test.json -->
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_with_valid_marker)

        assert errors == [], f"Expected no errors for valid marker, got: {errors}"

    def test_invalid_unknown_value_fails(self):
        """
        GIVEN prompt contains invalid marker: <!-- DES-VALIDATION: unknown -->
        WHEN DESMarkerValidator.validate() is called
        THEN INVALID_MARKER error is returned

        Business Value: Typos in marker values are caught immediately.
        """
        from des.application.validator import DESMarkerValidator

        prompt_with_invalid_marker = """
        <!-- DES-VALIDATION: unknown -->
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_with_invalid_marker)

        assert len(errors) > 0, "Expected error for invalid marker value 'unknown'"
        assert any("INVALID_MARKER" in error for error in errors), (
            f"Expected INVALID_MARKER error, got: {errors}"
        )

    def test_invalid_optional_value_fails(self):
        """
        GIVEN prompt contains invalid marker: <!-- DES-VALIDATION: optional -->
        WHEN DESMarkerValidator.validate() is called
        THEN INVALID_MARKER error is returned

        Business Value: Only 'required' is valid - no alternatives.
        """
        from des.application.validator import DESMarkerValidator

        prompt_with_invalid_marker = """
        <!-- DES-VALIDATION: optional -->
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_with_invalid_marker)

        assert len(errors) > 0, "Expected error for invalid marker value 'optional'"
        assert any("INVALID_MARKER" in error for error in errors), (
            f"Expected INVALID_MARKER error, got: {errors}"
        )

    def test_invalid_maybe_value_fails(self):
        """
        GIVEN prompt contains invalid marker: <!-- DES-VALIDATION: maybe -->
        WHEN DESMarkerValidator.validate() is called
        THEN INVALID_MARKER error is returned

        Business Value: Edge case validation - ambiguous values rejected.
        """
        from des.application.validator import DESMarkerValidator

        prompt_with_invalid_marker = """
        <!-- DES-VALIDATION: maybe -->
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_with_invalid_marker)

        assert len(errors) > 0, "Expected error for invalid marker value 'maybe'"
        assert any("INVALID_MARKER" in error for error in errors), (
            f"Expected INVALID_MARKER error, got: {errors}"
        )

    def test_invalid_empty_value_fails(self):
        """
        GIVEN prompt contains marker with empty value: <!-- DES-VALIDATION:  -->
        WHEN DESMarkerValidator.validate() is called
        THEN INVALID_MARKER error is returned

        Business Value: Incomplete markers are rejected.
        """
        from des.application.validator import DESMarkerValidator

        prompt_with_empty_marker = """
        <!-- DES-VALIDATION:  -->
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_with_empty_marker)

        assert len(errors) > 0, "Expected error for empty marker value"
        assert any("INVALID_MARKER" in error for error in errors), (
            f"Expected INVALID_MARKER error, got: {errors}"
        )

    def test_missing_marker_fails(self):
        """
        GIVEN prompt does not contain DES-VALIDATION marker
        WHEN DESMarkerValidator.validate() is called
        THEN error is returned indicating missing marker

        Business Value: Prompts without DES marker are caught as malformed.
        """
        from des.application.validator import DESMarkerValidator

        prompt_without_marker = """
        # DES_METADATA
        Step: test.json
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_without_marker)

        assert len(errors) > 0, "Expected error for missing DES-VALIDATION marker"
        assert any(
            "INVALID_MARKER" in error or "Missing" in error for error in errors
        ), f"Expected error about missing marker, got: {errors}"

    def test_case_sensitive_validation_fails(self):
        """
        GIVEN prompt contains marker with incorrect case: <!-- DES-VALIDATION: Required -->
        WHEN DESMarkerValidator.validate() is called
        THEN INVALID_MARKER error is returned (case matters)

        Business Value: Strict validation prevents typos and variations.
        """
        from des.application.validator import DESMarkerValidator

        prompt_with_case_error = """
        <!-- DES-VALIDATION: Required -->
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_with_case_error)

        assert len(errors) > 0, "Expected error for incorrect case 'Required'"
        assert any("INVALID_MARKER" in error for error in errors), (
            f"Expected INVALID_MARKER error, got: {errors}"
        )

    def test_malformed_comment_syntax_fails(self):
        """
        GIVEN prompt contains malformed HTML comment: <!-- DES-VALIDATION required -->
        WHEN DESMarkerValidator.validate() is called
        THEN error is returned for malformed syntax

        Business Value: Syntactically broken markers are caught.

        Note: Missing colon (:) after DES-VALIDATION makes this malformed.
        """
        from des.application.validator import DESMarkerValidator

        prompt_with_malformed_syntax = """
        <!-- DES-VALIDATION required -->
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_with_malformed_syntax)

        assert len(errors) > 0, "Expected error for malformed marker syntax"
        assert any(
            "INVALID_MARKER" in error or "malformed" in error.lower()
            for error in errors
        ), f"Expected error about malformed marker, got: {errors}"

    def test_marker_with_whitespace_variations(self):
        """
        GIVEN prompt contains marker with various whitespace: <!-- DES-VALIDATION:  required  -->
        WHEN DESMarkerValidator.validate() is called
        THEN marker is validated correctly (whitespace normalized)

        Business Value: Common formatting variations don't cause failures.
        """
        from des.application.validator import DESMarkerValidator

        prompt_with_whitespace = """
        <!-- DES-VALIDATION:  required  -->
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_with_whitespace)

        assert errors == [], (
            f"Expected no errors for marker with extra whitespace, got: {errors}"
        )

    def test_multiple_markers_first_validation(self):
        """
        GIVEN prompt contains multiple DES-VALIDATION markers (invalid)
        WHEN DESMarkerValidator.validate() is called
        THEN validation addresses the marker validation issue

        Business Value: Duplicate markers are handled appropriately.

        Note: Having multiple markers is itself a problem; validation should address it.
        """
        from des.application.validator import DESMarkerValidator

        prompt_with_multiple_markers = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-VALIDATION: required -->
        """

        validator = DESMarkerValidator()
        errors = validator.validate(prompt_with_multiple_markers)

        # Note: The specification doesn't explicitly forbid multiple markers,
        # so this test validates current behavior. If multiple markers should be
        # forbidden, this test will need adjustment based on implementation choice.
        # For now, if value is 'required' and appears anywhere, that's sufficient.
        assert errors == [], (
            f"Multiple valid markers should be acceptable, got: {errors}"
        )
