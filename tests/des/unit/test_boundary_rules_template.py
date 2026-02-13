"""
Unit tests for BoundaryRulesTemplate rendering.

Tests the BOUNDARY_RULES section rendering for US-007, verifying that
prompts include explicit scope constraints for agents.
"""

from des.application.boundary_rules_template import BoundaryRulesTemplate


class TestBoundaryRulesTemplateRendering:
    """
    Unit tests for BoundaryRulesTemplate.render() method.

    Validates that the template renders a complete BOUNDARY_RULES section
    with proper markdown structure and required subsections.
    """

    def test_render_includes_section_header(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN result includes '## BOUNDARY_RULES' section header

        Business Context:
        The BOUNDARY_RULES section is one of 9 mandatory DES sections.
        Without the proper header, validation will fail and block Task invocation.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: Section header present
        assert "## BOUNDARY_RULES" in result, (
            "Section header '## BOUNDARY_RULES' must be present for DES validation"
        )

    def test_render_includes_allowed_subsection(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN result includes 'ALLOWED' subsection

        Business Context:
        Agents need an explicit whitelist of permitted actions and files.
        The ALLOWED subsection defines what the agent can modify.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: ALLOWED subsection present
        assert "ALLOWED" in result, (
            "ALLOWED subsection must be present to define permitted agent actions"
        )

    def test_render_includes_forbidden_subsection(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN result includes 'FORBIDDEN' subsection

        Business Context:
        Agents need explicit prohibition against scope creep.
        The FORBIDDEN subsection prevents "helpful" but out-of-scope modifications.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: FORBIDDEN subsection present
        assert "FORBIDDEN" in result, (
            "FORBIDDEN subsection must be present to prevent scope creep"
        )

    def test_render_returns_multiline_string(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN result is a non-empty multiline string

        Business Context:
        The BOUNDARY_RULES section must have structure, not just a single line.
        Multiple lines allow for header, ALLOWED list, FORBIDDEN list.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: Multiline string
        assert isinstance(result, str), "Result must be a string"
        assert len(result) > 0, "Result must not be empty"
        assert "\n" in result, "Result must be multiline (contain newlines)"

    def test_render_section_header_precedes_subsections(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN section header appears before ALLOWED and FORBIDDEN subsections

        Business Context:
        Proper markdown structure requires the ## BOUNDARY_RULES header
        to appear before the subsection content.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: Header precedes subsections
        header_pos = result.find("## BOUNDARY_RULES")
        allowed_pos = result.find("ALLOWED")
        forbidden_pos = result.find("FORBIDDEN")

        assert header_pos < allowed_pos, (
            "Section header must appear before ALLOWED subsection"
        )
        assert header_pos < forbidden_pos, (
            "Section header must appear before FORBIDDEN subsection"
        )

    def test_forbidden_includes_other_step_files_prohibition(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN FORBIDDEN section explicitly mentions 'other step files'

        Business Context:
        Priya saw an agent modify step 02-03.json while working on 01-01.json,
        causing merge conflicts. Explicit prohibition against other step files
        prevents such scope violations.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: Other step files explicitly forbidden
        other_steps_forbidden = any(
            phrase in result.lower()
            for phrase in ["other step", "different step", "other task"]
        )
        assert other_steps_forbidden, (
            "FORBIDDEN must explicitly mention 'other step files' or similar - "
            "agents should not modify steps outside their assignment"
        )

    def test_forbidden_includes_unrelated_files_prohibition(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN FORBIDDEN section mentions files outside scope/unrelated files

        Business Context:
        An agent "improved" AuthService while working on UserRepository,
        causing unintended side effects. Generic prohibition prevents
        modifications to files not in scope.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: Unrelated files forbidden
        unrelated_forbidden = any(
            phrase in result.lower()
            for phrase in ["other file", "unrelated", "outside scope", "not in scope"]
        )
        assert unrelated_forbidden, (
            "FORBIDDEN must include reference to files outside scope or unrelated files - "
            "prevents well-intentioned but out-of-scope modifications"
        )

    def test_forbidden_includes_comprehensive_categories(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN FORBIDDEN section covers: config files, production deployment

        Business Context:
        Generic prohibitions prevent common scope expansion patterns:
        - Modifying config files unless explicitly in scope
        - Production deployment changes
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()
        result_lower = result.lower()

        # THEN: Comprehensive categories covered
        # Note: At least one of these patterns should be present
        config_or_deployment = any(
            phrase in result_lower
            for phrase in [
                "config",
                "configuration",
                "deployment",
                "production",
                "not specified",
                "not in scope",
            ]
        )
        assert config_or_deployment, (
            "FORBIDDEN should cover configuration or deployment files - "
            "common sources of scope creep"
        )

    def test_forbidden_includes_continuation_prohibition(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN FORBIDDEN section prohibits continuing to next step

        Business Context:
        After completing step 01-01, an agent might think it's efficient
        to continue to step 01-02. This violates the principle of returning
        control to Marcus for explicit next-step initiation.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: Continuation to next step forbidden
        continuation_forbidden = any(
            phrase in result.lower()
            for phrase in ["next step", "continue to", "subsequent step"]
        )
        assert continuation_forbidden, (
            "FORBIDDEN must prohibit continuing to next step - "
            "agent must return control after completion"
        )

    def test_forbidden_emphasizes_return_control_immediately(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN FORBIDDEN section emphasizes RETURN CONTROL IMMEDIATELY (caps)

        Business Context:
        Strong emphasis needed to prevent agents from autonomously continuing.
        CAPS indicates critical instruction that must not be ignored.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: Strong emphasis on returning control
        has_caps_emphasis = "RETURN CONTROL IMMEDIATELY" in result
        assert has_caps_emphasis, (
            "FORBIDDEN must emphasize 'RETURN CONTROL IMMEDIATELY' in CAPS - "
            "critical instruction requires visual emphasis"
        )

    def test_forbidden_mentions_explicit_marcus_initiation(self):
        """
        GIVEN BoundaryRulesTemplate instance
        WHEN render() is called
        THEN FORBIDDEN section mentions Marcus in context of next step initiation

        Business Context:
        Clarifies the workflow: Marcus (user) controls step progression,
        not the agent. Agent completes current step and halts.
        """
        template = BoundaryRulesTemplate()

        # WHEN: Render the template
        result = template.render()

        # THEN: Mentions Marcus in continuation context
        # Look in FORBIDDEN section specifically
        forbidden_section_start = result.find("**FORBIDDEN**:")
        forbidden_section = (
            result[forbidden_section_start:]
            if forbidden_section_start != -1
            else result
        )

        mentions_marcus_workflow = "marcus" in forbidden_section.lower()
        assert mentions_marcus_workflow, (
            "FORBIDDEN section should mention Marcus in context of step initiation - "
            "clarifies user-controlled workflow (Marcus explicitly starts next step)"
        )
