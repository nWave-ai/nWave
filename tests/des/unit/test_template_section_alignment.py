"""
Test that the DES execute template contains all mandatory sections
required by the validator.

This prevents drift between the validator's MANDATORY_SECTIONS list
and the actual template content in execute.md.
"""

import re
from pathlib import Path

from des.application.validator import MandatorySectionChecker


def _find_project_root() -> Path:
    """Find the project root by locating pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not find project root (no pyproject.toml found)")


def _extract_template_code_block(template_path: Path) -> str:
    """Extract the DES template code block containing DES-VALIDATION marker.

    The template has nested indented code blocks (e.g., commit message examples),
    so we match only unindented ``` delimiters at the start of a line.
    """
    content = template_path.read_text(encoding="utf-8")
    # Match code blocks delimited by ``` at the start of a line (not indented).
    # This avoids matching indented ``` inside the template (nested examples).
    for match in re.finditer(r"^```\n(.*?)^```", content, re.DOTALL | re.MULTILINE):
        block = match.group(1)
        if "DES-VALIDATION" in block:
            return block
    raise ValueError(f"No DES template code block found in {template_path}")


def test_execute_template_contains_all_mandatory_sections():
    """Every section in MandatorySectionChecker.MANDATORY_SECTIONS must
    appear as a '# SECTION_NAME' header inside the execute.md template
    code block."""
    project_root = _find_project_root()
    template_path = project_root / "nWave" / "tasks" / "nw" / "execute.md"

    template_block = _extract_template_code_block(template_path)

    # Extract all section headers from the template code block
    headers_in_template = set(re.findall(r"^# (\w+)", template_block, re.MULTILINE))

    mandatory = set(MandatorySectionChecker.MANDATORY_SECTIONS)
    missing = mandatory - headers_in_template

    assert not missing, (
        f"Template execute.md is missing mandatory section(s): {sorted(missing)}. "
        f"The validator requires these sections but the template does not contain them. "
        f"Add '# SECTION_NAME' headers to the template code block."
    )
