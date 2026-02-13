"""DES validation marker generation for Task prompts.

Generates HTML comment markers that indicate DES validation requirements
for execute/develop commands.
"""


class DESMarkerGenerator:
    """Generates DES validation markers for Task prompts."""

    def generate_markers(self, command: str, step_file: str) -> str:
        """Generate DES validation markers for execute/develop commands.

        Args:
            command: Command type (e.g., "/nw:execute", "/nw:develop")
            step_file: Path to step file

        Returns:
            Formatted DES marker string with validation, step file, origin markers

        Raises:
            ValueError: If command or step_file is None or empty
        """
        # Validate command parameter
        if not command:
            raise ValueError("Command cannot be None or empty")

        # Validate step_file parameter
        if not step_file:
            raise ValueError("Step file cannot be None or empty")

        markers = [
            "<!-- DES-VALIDATION: required -->",
            f"<!-- DES-STEP-FILE: {step_file} -->",
            f"<!-- DES-ORIGIN: command:{command} -->",
        ]
        return "\n".join(markers)
