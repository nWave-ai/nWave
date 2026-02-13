"""
Test that execute.md TDD phases stay in sync with validator source of truth.

The source file uses {{MANDATORY_PHASES}} template variable which is resolved
at install time from step-tdd-cycle-schema.json. This test verifies:
1. Source contains the template variable (not hardcoded phases)
2. Source declares Schema v4.0 and references TDDPhaseValidator
"""


class TestExecuteTemplateSync:
    """Verify execute.md TDD phases use template injection."""

    def test_source_uses_template_variable(self):
        """
        GIVEN execute.md source file
        WHEN we check the build-system TDD_PHASES section (## heading)
        THEN it contains {{MANDATORY_PHASES}} template variable, not hardcoded phases
        """
        with open("nWave/tasks/nw/execute.md") as f:
            content = f.read()

        # Find the build-system section (## heading), not the DES prompt template
        # (# heading inside a code block). The build-system section uses ## TDD_PHASES.
        tdd_section_start = content.find("\n## TDD_PHASES")
        assert tdd_section_start != -1, "## TDD_PHASES section not found in execute.md"

        section = content[tdd_section_start : tdd_section_start + 500]

        assert "{{MANDATORY_PHASES}}" in section, (
            "execute.md source must use {{MANDATORY_PHASES}} template variable"
        )

    def test_source_declares_schema_v4(self):
        """
        GIVEN execute.md source file
        WHEN we check the build-system TDD_PHASES section comment (## heading)
        THEN it declares Schema v4.0 and references TDDPhaseValidator
        """
        with open("nWave/tasks/nw/execute.md") as f:
            content = f.read()

        # Find the build-system section (## heading), not the DES prompt template
        tdd_section_start = content.find("\n## TDD_PHASES")
        assert tdd_section_start != -1, "## TDD_PHASES section not found"

        section = content[tdd_section_start : tdd_section_start + 300]

        assert "Schema v4.0" in section, (
            "execute.md must declare 'Schema v4.0' in TDD_PHASES section"
        )

        assert "TDDPhaseValidator.MANDATORY_PHASES" in section, (
            "execute.md must reference TDDPhaseValidator.MANDATORY_PHASES"
        )
