"""US-4 / DESIGN D-5 — Copilot has no install path: an xfail(strict=True) test.

The installer has NO GitHub Copilot platform (research-only, backlog #19). This
is NOT a CI lane (a lane asserting absence wastes runner minutes). Instead a
single strict-xfail unit test asserts "looking up a Copilot contract fails".

The day someone wires Copilot support, ``tool_contract("copilot")`` stops
raising, this test XPASSes, and ``strict=True`` turns the XPASS into a HARD
failure — forcing whoever added the path to delete this placeholder.

Layer 1 unit (no real I/O). Imports the production registry lookup directly
(the registry's driving port). Currently RED-scaffold: the lookup raises an
AssertionError for ALL tools, so the xfail body raises and the test xfails —
which is the desired pending state until DELIVER implements the registry. Once
the registry exists, it must STILL raise for "copilot" (and only "copilot"
stays absent), keeping this xfail.
"""

from __future__ import annotations

import pytest

from scripts.release.rc_smoke.contracts import tool_contract
from tests.release.rc_smoke.acceptance.steps.domain_types import UnsupportedTool


@pytest.mark.xfail(
    strict=True,
    reason="Copilot has no install path (backlog #19); remove this test the day it does.",
)
def test_copilot_has_no_install_path() -> None:
    # If this returns a contract (no exception), Copilot support exists and the
    # XPASS+strict converts to a hard failure — exactly the forcing function.
    contract = tool_contract(UnsupportedTool.COPILOT.value)
    assert contract is not None
