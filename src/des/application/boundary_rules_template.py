"""
BOUNDARY_RULES template for DES-validated prompts.

This module defines the structure and content for the BOUNDARY_RULES section
that prevents agent scope creep by explicitly defining allowed and forbidden actions.
"""


class BoundaryRulesTemplate:
    """
    Template for BOUNDARY_RULES section in DES-validated prompts.

    The section includes:
    1. Section header (## BOUNDARY_RULES)
    2. ALLOWED subsection (permitted files and actions)
    3. FORBIDDEN subsection (prohibited actions and scope expansion)
    """

    def render(self, allowed_patterns: list[str] | None = None) -> str:
        """
        Render the complete BOUNDARY_RULES section.

        Args:
            allowed_patterns: List of allowed file patterns from BoundaryRulesGenerator.
                            If None, uses generic patterns.

        Returns:
            str: Markdown-formatted section with header, ALLOWED, and FORBIDDEN subsections
        """
        if allowed_patterns:
            # Format patterns as bullet list
            pattern_bullets = "\n".join(f"- {pattern}" for pattern in allowed_patterns)
            allowed_section = f"""**ALLOWED**:
{pattern_bullets}
- Modify step file to record phase outcomes and state changes"""
        else:
            allowed_section = """**ALLOWED**:
- Modify step file to record phase outcomes and state changes
- Modify task implementation files as specified in step scope
- Modify test files matching the feature being implemented"""

        forbidden_section = """**FORBIDDEN**:
- Modify other step files or tasks outside current assignment
- Modify files not specified in step scope or allowed patterns
- Modify unrelated source files outside scope (e.g., AuthService when working on UserRepository)
- Modify configuration files unless explicitly in scope
- Modify production deployment files
- Continue to next step after completion - RETURN CONTROL IMMEDIATELY. Marcus will explicitly start the next step when ready.
"""

        return f"""## BOUNDARY_RULES

{allowed_section}

{forbidden_section}"""
