"""
TIMEOUT_INSTRUCTION template for DES-validated prompts.

This module defines the structure and content for the TIMEOUT_INSTRUCTION section
that enables agent self-regulation without programmatic turn limits.
"""


class TimeoutInstructionTemplate:
    """
    Template for TIMEOUT_INSTRUCTION section in DES-validated prompts.

    The section includes 4 required elements:
    1. Turn budget (~50 turns)
    2. Progress checkpoints (turn ~10, ~25, ~40, ~50)
    3. Early exit protocol
    4. Turn logging instruction
    """

    def render(self) -> str:
        """
        Render the complete TIMEOUT_INSTRUCTION section.

        Returns:
            str: Markdown-formatted section with all 4 elements
        """
        return f"""## TIMEOUT_INSTRUCTION

{self._render_turn_budget()}

{self._render_progress_checkpoints()}

{self._render_early_exit_protocol()}

{self._render_turn_logging()}
"""

    def _format_instruction_element(self, header: str, content: str) -> str:
        """
        Format instruction element with consistent markdown structure.

        Extracts common formatting pattern used by all 4 helper methods:
        **Header**: content

        Args:
            header: Element header text (e.g., "Turn Budget")
            content: Element content text (may be multiline)

        Returns:
            Formatted markdown string with **Header**: content pattern
        """
        return f"**{header}**: {content}"

    def _render_turn_budget(self) -> str:
        """Render turn budget element (~50 turns)."""
        return self._format_instruction_element(
            header="Turn Budget",
            content="Aim to complete this task within approximately 50 turns.",
        )

    def _render_progress_checkpoints(self) -> str:
        """Render progress checkpoints with TDD phase mapping."""
        content = """Track your progress against these milestones:
- Turn ~10: PREPARE and RED phases should be complete
- Turn ~25: GREEN phases should be complete
- Turn ~40: REFACTOR phases should be complete
- Turn ~50: COMMIT phase starting (on track for completion)"""
        return self._format_instruction_element(
            header="Progress Checkpoints", content=content
        )

    def _render_early_exit_protocol(self) -> str:
        """Render early exit protocol steps."""
        content = """If you cannot complete the task within the turn budget:
1. Save your current progress to the step file
2. Set the current phase to IN_PROGRESS with detailed notes
3. Return with status explaining what's blocking completion
4. Do not continue if stuck - request human guidance"""
        return self._format_instruction_element(
            header="Early Exit Protocol", content=content
        )

    def _render_turn_logging(self) -> str:
        """Render turn logging instruction with example format."""
        content = """Log your turn count at each phase transition using this format:
- Example: `[Turn 15] Starting GREEN_UNIT phase`
- Example: `[Turn 32] Completed REFACTOR_L2 phase`

This helps track execution pacing and identify phases consuming excessive turns."""
        return self._format_instruction_element(header="Turn Logging", content=content)
