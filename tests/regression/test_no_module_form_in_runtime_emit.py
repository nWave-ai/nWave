"""Regression guard: src/des/ runtime MUST NOT emit module-form CLI invocation.

Background (Rex RCA 2026-05-13, Issue 1):
Module-form usage strings (`python -m des.cli.X`, `PYTHONPATH=src python -m des.cli.X`)
were leaking from `src/des/` runtime CLI emit into the agent context, causing
Claude to generalize the module form as canonical. Under multi-env setups
(uv install nwave-ai + poetry project), module form fails because `des` is
in the pipx venv only — entry-point form (`des-roadmap`, `des-init-log`,
`des-log-phase`, `des-verify-integrity`, `des-health-check`) works
env-agnostically via PATH.

Prior regression guards (`tests/e2e/test_python_portability_fallback.py`,
`tests/bugs/test_issue_36_permission_prompts_des_cli.py`) scoped to
`nWave/templates/` and 3 skill files — missed `src/`. This test closes the
scope gap.

Refs: `docs/feature/fix-des-cli-env-collision/discuss/rca.md`
"""

from __future__ import annotations

import re
from pathlib import Path


_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"python\s*-m\s+des\.cli\."),
    re.compile(r"PYTHONPATH\s*=\s*\S*\s+python\s*-m\s+des\.cli\."),
    re.compile(r"python3\s*-m\s+des\.cli\."),
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DES = _PROJECT_ROOT / "src" / "des"


def _collect_src_des_py_files() -> list[Path]:
    """All .py files under src/des/ — sorted for stable test IDs."""
    return sorted(_SRC_DES.rglob("*.py"))


def _scan_file(path: Path) -> list[tuple[int, str]]:
    """Return list of (line_number, matched_text) for any forbidden pattern."""
    hits: list[tuple[int, str]] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in _FORBIDDEN_PATTERNS:
            match = pattern.search(line)
            if match:
                hits.append((lineno, line.strip()))
                break  # one hit per line is enough
    return hits


def test_src_des_runtime_has_no_module_form_invocations() -> None:
    """∀ f ∈ src/des/**/*.py : ¬∃ line ∈ f matching forbidden_pattern.

    Closed-world static invariant over the project's runtime tree. Collapses
    155 parametrized cases (one per file) into a single set-difference assertion
    that reports the full violation map in the failure message.

    Module-form strings (e.g. `python -m des.cli.roadmap`) leaked from runtime
    emit cause Claude to generalize the form, breaking multi-env users
    (uv install + poetry/conda/venv project). Use entry-point form instead:
    `des-roadmap`, `des-init-log`, `des-log-phase`, `des-verify-integrity`,
    `des-health-check` (declared in pyproject.toml under `[project.scripts]`).

    Shape choice (Lyra 2026-05-18 after PBT-pilot falsification): set-difference
    collapse, not PBT. Per `nw-test-optimization` SKILL section 2-3 (parametrize-
    inflation → set-difference). Hypothesis would add 457ms import + per-example
    overhead x 155, making it slower than parametrize. Mandate-12 still satisfied:
    types-as-domain (`Path` enumeration), services-as-logic (`_scan_file` +
    `_FORBIDDEN_PATTERNS`), single-source assertion. Empirical wall-time:
    5.42s parametrize → 0.61s collapse (8.9x faster, 88.7% reduction).
    """
    violations = {
        py_file: hits
        for py_file in _collect_src_des_py_files()
        if (hits := _scan_file(py_file))
    }
    assert not violations, (
        "Forbidden module-form CLI invocation in src/des/:\n"
        + "\n".join(
            f"  {path.relative_to(_PROJECT_ROOT)}:{n}: {text}"
            for path, hits in violations.items()
            for n, text in hits
        )
        + "\n\nUse entry-point form instead (e.g. `des-roadmap` not `python -m des.cli.roadmap`)."
        + "\nDeclared entry points: pyproject.toml [project.scripts]."
    )
