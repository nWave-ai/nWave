"""SSOT regression: build-time wheel validator must mirror e2e privacy contract.

The build-time validator (``scripts/validation/validate_wheel_contents.py``)
and the post-publish e2e privacy contract
(``tests/e2e/test_wheel_privacy_contract.py``) historically drifted: the
e2e gate gained 6 categories on 2026-04-24 while the build-time gate
stayed at 5. The drift let scripts/hooks/ files leak into the wheel and
caused the post-publish gate to self-block.

This test pins the SSOT invariant: ``build_wheel_manifest().forbidden_prefixes``
MUST be a superset of the canonical e2e privacy contract categories. Any
new category added to the e2e contract is mechanically forced into the
build-time validator too.

Step-Id: 01-01
"""

from __future__ import annotations

from scripts.validation.validate_wheel_contents import build_wheel_manifest


# Canonical privacy contract categories, derived from the docstring of
# ``tests/e2e/test_wheel_privacy_contract.py`` (lines 7-19). When a new
# category is added there, add it here too — that propagation is the
# whole point of this regression test.
EXPECTED_FORBIDDEN_PREFIXES: frozenset[str] = frozenset(
    {
        "docs/analysis/",
        "docs/feature/",
        ".github/",
        "src/des/",
        "tests/",
        "pyproject.toml",
        "scripts/release/",
        "scripts/hooks/",
        "scripts/framework/",
        "scripts/validation/",
    }
)


def test_build_wheel_manifest_is_superset_of_e2e_privacy_contract() -> None:
    """build_wheel_manifest().forbidden_prefixes ⊇ EXPECTED_FORBIDDEN_PREFIXES."""
    manifest = build_wheel_manifest()
    actual = frozenset(manifest.forbidden_prefixes)

    missing = EXPECTED_FORBIDDEN_PREFIXES - actual
    assert not missing, (
        f"build_wheel_manifest() forbidden_prefixes is missing categories "
        f"present in the e2e privacy contract: {sorted(missing)}. "
        f"Add them to scripts/validation/validate_wheel_contents.py."
    )
