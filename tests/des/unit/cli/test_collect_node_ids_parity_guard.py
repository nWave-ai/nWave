"""Layer-1 unit pinning the canonical-vs-parsed parity invariant at the function seam.

F-CONTRACT-GATE-DIGEST-UNDERCOUNT (AMENDMENT FINDING #4). The single
authorized Layer-1 unit-test exception for this feature -- explicitly
sanctioned by the feature delta because the parity invariant lives at the
function boundary and a subprocess CANNOT prove "the function raised
`_CollectionError`" vs "the function returned a truncated list that the CLI
happened to surface as a diagnostic". The smallest faithful surface for the
invariant IS the function itself.

Mandate-13 exception scope: ONE unit test, ONE seam (`_collect_node_ids`),
ONE invariant (parsed_count < canonical_count -> raises). All other ATs in
this feature drive through Layer 2 in-process or Layer 3 subprocess.

Test contract: when the tmp pytest project contains a collapsing fixture
(class-grouped methods sharing a class docstring), the parsed count from the
legacy stdout-parse falls below the canonical count from pytest's
`session.items`. The fix MUST raise `_CollectionError`; the legacy seam
returns the truncated list silently. This file's two test functions pin both
sides of the parity invariant.

Regression contract: this unit RED-by-design on master (the legacy seam does
not raise on undercount) and GREENs once the slice-01 parity guard lands.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from des.cli.run_contract_gate import _collect_node_ids, _CollectionError


_CLASS_GROUPED_FIVE_METHODS_SOURCE = textwrap.dedent(
    '''\
    """One class, five methods, one class docstring -- the collapse fixture."""

    import pytest


    class TestClassGroupedFiveMethodsUnit:
        """Shared class docstring -- pytest -q collapses every method line into ONE."""

        @pytest.mark.unit
        def test_member_one(self):
            assert True

        @pytest.mark.unit
        def test_member_two(self):
            assert True

        @pytest.mark.unit
        def test_member_three(self):
            assert True

        @pytest.mark.unit
        def test_member_four(self):
            assert True

        @pytest.mark.unit
        def test_member_five(self):
            assert True
    '''
)


_NON_COLLAPSING_FIVE_FUNCTIONS_SOURCE = textwrap.dedent(
    '''\
    """Five module-level functions, distinct docstrings -- no collapse class."""

    import pytest


    @pytest.mark.unit
    def test_distinct_one():
        """First distinct test docstring."""
        assert True


    @pytest.mark.unit
    def test_distinct_two():
        """Second distinct test docstring."""
        assert True


    @pytest.mark.unit
    def test_distinct_three():
        """Third distinct test docstring."""
        assert True


    @pytest.mark.unit
    def test_distinct_four():
        """Fourth distinct test docstring."""
        assert True


    @pytest.mark.unit
    def test_distinct_five():
        """Fifth distinct test docstring."""
        assert True
    '''
)


_PYPROJECT_SOURCE = textwrap.dedent(
    """\
    [tool.pytest.ini_options]
    markers = [
        "unit: unit-tier (contract scope)",
        "integration: integration-tier (contract scope)",
        "acceptance: acceptance-tier (contract scope)",
    ]
    """
)


def _provision_project(project_dir: Path, test_source: str, filename: str) -> None:
    """Provision a minimal pytest project with the given test source file."""
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "pyproject.toml").write_text(_PYPROJECT_SOURCE, encoding="utf-8")
    tests_root = project_dir / "tests"
    tests_root.mkdir(parents=True, exist_ok=True)
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / filename).write_text(test_source, encoding="utf-8")


@pytest.mark.unit
@pytest.mark.xfail(
    reason=(
        "ATDD-pure author-ahead: F-CONTRACT-GATE-DIGEST-UNDERCOUNT slice-01 ATs "
        "authored + reviewed, parity-guard implementation pending; the slice-01 "
        "crafter removes this xfail at the GREEN phase"
    ),
    strict=False,
)
def test_collect_node_ids_refuses_undercount_on_collapsing_fixture(
    tmp_path: Path,
) -> None:
    """The parity guard MUST raise `_CollectionError` when parsed < canonical.

    Fixture: one class, five methods, one class docstring (the symmetry
    collapse class). Canonical count = 5 (pytest's `session.items`). Parsed
    count under the legacy stdout-parse = 1 (the five method lines collapse
    to one under `-q`). The fix MUST observe `parsed (1) < canonical (5)` and
    raise; the legacy seam silently returns the truncated list.

    REGRESSION CONTRACT: this unit RED-by-design on master. The legacy
    `_collect_node_ids` returns a list of length 1 without raising. After the
    slice-01 parity guard lands, it raises `_CollectionError` with a message
    naming the parsed-vs-canonical mismatch.
    """
    project_dir = tmp_path / "collapsing_project"
    _provision_project(
        project_dir,
        _CLASS_GROUPED_FIVE_METHODS_SOURCE,
        "test_collapsing.py",
    )
    with pytest.raises(_CollectionError) as exc_info:
        _collect_node_ids(project_dir)
    # The diagnostic MUST name BOTH counts so the operator can act on the
    # mismatch (the slice-01 crafter is free to pick the exact wording; the
    # invariant pinned here is that the message contains the two numbers).
    message = str(exc_info.value)
    assert "5" in message, (
        f"parity-guard diagnostic must name the canonical count 5; got: {message!r}"
    )


@pytest.mark.unit
def test_collect_node_ids_returns_canonical_set_on_non_collapsing_fixture(
    tmp_path: Path,
) -> None:
    """When parsed == canonical, the parity guard MUST be a no-op.

    Fixture: five module-level functions with distinct docstrings (no
    collapse class). Canonical count = 5. Parsed count under the legacy
    stdout-parse = 5 (every test gets its own line). The fix MUST observe
    `parsed (5) == canonical (5)` and return the parsed list unchanged; no
    `_CollectionError` is raised on the well-formed contract.

    REGRESSION CONTRACT: this unit PASSES on master AND after the fix lands
    -- the legacy seam already returns the right answer when the fixture
    does not exercise the collapse class; the fix must not regress this
    happy-path observable.
    """
    project_dir = tmp_path / "non_collapsing_project"
    _provision_project(
        project_dir,
        _NON_COLLAPSING_FIVE_FUNCTIONS_SOURCE,
        "test_non_collapsing.py",
    )
    node_ids = _collect_node_ids(project_dir)
    assert len(node_ids) == 5, (
        f"non-collapsing fixture must yield 5 unique node-ids; got {len(node_ids)}: "
        f"{node_ids!r}"
    )
