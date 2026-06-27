"""
Unit tests for MarkdownSectionParser — driving through the parser's
public API (its parse() method IS the driving port for this pure domain
function). Port-to-port: caller supplies text, asserts on returned model.

Test Budget: 1 behavior (parser emits WaveSection + CommitmentRow events
from token-billing exemplar text) x 2 = 2 unit tests max. Using 1.
"""

from __future__ import annotations

from nwave_ai.feature_delta.domain.model import FeatureDeltaModel
from nwave_ai.feature_delta.domain.parser import MarkdownSectionParser


TOKEN_BILLING_TEXT = (
    "# token-billing\n\n"
    "## Wave: DISCUSS\n\n"
    "### [REF] Inherited commitments\n\n"
    "| Origin | Commitment | DDD | Impact |\n"
    "|--------|------------|-----|--------|\n"
    "| n/a | real WSGI handler bound to /api/usage | n/a | "
    "establishes protocol surface |\n\n"
    "## Wave: DESIGN\n\n"
    "### [REF] Inherited commitments\n\n"
    "| Origin | Commitment | DDD | Impact |\n"
    "|--------|------------|-----|--------|\n"
    "| DISCUSS#row1 | framework-agnostic dispatcher | "
    "(none) | tradeoffs apply across the stack |\n"
)


def test_parser_emits_two_wave_sections_with_commitment_rows():
    """
    Parser driving port: parse(text) -> FeatureDeltaModel.

    Given the token-billing exemplar text,
    the parser must emit a model with DISCUSS and DESIGN sections,
    each containing one CommitmentRow — proving the state machine
    traverses Wave headings and commitment table rows correctly.
    """
    parser = MarkdownSectionParser()
    model = parser.parse(TOKEN_BILLING_TEXT)

    assert isinstance(model, FeatureDeltaModel)
    section_names = [s.name for s in model.sections]
    assert "DISCUSS" in section_names
    assert "DESIGN" in section_names

    discuss = next(s for s in model.sections if s.name == "DISCUSS")
    assert len(discuss.rows) == 1
    assert "WSGI" in discuss.rows[0].commitment

    design = next(s for s in model.sections if s.name == "DESIGN")
    assert len(design.rows) == 1
    assert "framework-agnostic" in design.rows[0].commitment
    assert design.rows[0].ddr in ("(none)", "none", "")
