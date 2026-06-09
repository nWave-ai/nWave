"""Composition root for the slice-plan-validation acceptance slice.

ADR-028 D2 + ADR-029 D3 / slice-06 (Mandate-12, Pillar 3). Wires the PRODUCTION
validate-feature-delta CLI entry point
(``scripts.validation.validate_feature_delta.main``) against a tmp_path
feature-delta fixture. Business logic lives here as the single source of truth;
step bodies delegate to ``SlicePlanValidationComposition`` methods and never
inline logic.

Layer 3 (subprocess/FS acceptance): the validator CLI is the driving port; the
only driven port is the real filesystem (tmp_path). No PBT machinery
(Mandate 9/11).

Pure-function contract (ADR-028 Reuse Analysis -- ``validate_feature_delta.py``
keeps its pure functional core ``validate_feature_delta_content``): the CLI
reads the feature-delta and returns a verdict (exit code + stdout); it performs
NO filesystem mutation. ``capture_universe`` snapshots the feature-delta so the
When-step state-delta guard proves the read-only contract (Mandate 8).

Structured-verdict contract (pins the slice-06 CLI's machine output -- this is
the contract the crafter MUST implement, not a guess):

    The slice-06 ``--require-slice-plan`` mode is invoked together with
    ``--format=json``. In that mode the CLI emits to stdout exactly ONE JSON
    object (single line) carrying a stable ``"verdict"`` field whose value is
    one of the closed token set::

        accepted | missing-slice-plan | malformed-slice-plan
                 | malformed-wave-heading

    The verdict mapping below reads that ``verdict`` token -- a STRUCTURED
    contract -- never free-text stdout substrings. The token set is closed:
    ``_VERDICT_TOKEN`` maps each token to a ``SlicePlanVerdict``; an unknown or
    absent token raises rather than silently defaulting, so a crafter that
    emits an off-contract token fails loudly (no silent misclassification).

RED scaffold note: on master ``validate_feature_delta.main`` accepts neither
``--require-slice-plan`` nor ``--format=json`` -- invoked with extra arguments
it prints usage and returns exit 1, emitting no JSON line. Every
``--require-slice-plan`` assertion therefore FAILS on master (no ``verdict``
token to read -> ``UNRECOGNISED_INVOCATION``) and PASSES once slice-06 extends
the CLI. The import resolves cleanly on master (the module exists today); the
RED signal is a missing structured verdict, not a collection error -- a
deliberate missing-functionality RED.
"""

from __future__ import annotations

import contextlib
import io
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

# Production driving port -- the validate-feature-delta CLI. The module exists
# on master; slice-06 EXTENDS its `main` with the --require-slice-plan flag.
from scripts.validation.validate_feature_delta import (
    main as validate_feature_delta_main,
)

from .domain_types import CheckMode, FeatureId, SlicePlanShape, SlicePlanVerdict


# The five required slice-plan columns, fixed order (ADR-028 D2 L137).
_SLICE_PLAN_COLUMNS = (
    "Slice",
    "Value statement",
    "Status",
    "Annotation",
    "Justification",
)

# The closed `verdict` token set the slice-06 CLI emits under
# --require-slice-plan --format=json. This mapping IS the structured contract
# the slice-06 crafter must implement -- the AT reads the token, never a
# free-text stdout substring. An off-contract or absent token raises (see
# `ValidationResult.verdict`) so a wrong token fails loudly, never silently
# misclassifies.
_VERDICT_TOKEN: dict[str, SlicePlanVerdict] = {
    "accepted": SlicePlanVerdict.ACCEPTED,
    "missing-slice-plan": SlicePlanVerdict.MISSING_SLICE_PLAN,
    "malformed-slice-plan": SlicePlanVerdict.MALFORMED_SLICE_PLAN,
    "malformed-wave-heading": SlicePlanVerdict.MALFORMED_WAVE_HEADING,
}

# A single well-formed slice row used by the happy-path fixtures.
_WS_ROW = (
    "| slice-01 | Operator previews a plan | pending | @walking-skeleton | "
    "thinnest end-to-end vertical |"
)


@dataclass
class ValidationResult:
    """Observable outcome of one validate-feature-delta CLI invocation.

    ``mode`` records which invocation produced this result, because the two
    modes have two DIFFERENT observable contracts:

    - ``CheckMode.PLAIN`` -- the pre-existing heading-form CLI. Its contract is
      exit code only (0 valid / non-zero malformed). It emits plain text, not
      JSON. This contract is unchanged on master and forever.
    - ``CheckMode.REQUIRE_SLICE_PLAN`` -- the slice-06 ``--format=json`` mode.
      Its contract is a single JSON object with a stable ``verdict`` token.

    The verdict is read per-mode so the plain-mode no-regression pin is never
    misclassified by the structured-token reader (which only applies to JSON
    mode).
    """

    mode: CheckMode
    exit_code: int
    output: str

    @property
    def _verdict_token(self) -> str | None:
        """The ``verdict`` field of the single JSON object the CLI emits.

        Under ``--require-slice-plan --format=json`` the slice-06 CLI emits
        exactly one JSON object (single line) to stdout. This returns its
        ``verdict`` field, or ``None`` when stdout carries no parseable JSON
        object with a ``verdict`` key (the master state -- the CLI does not
        emit JSON, it prints a ``usage:`` banner).
        """
        for line in self.output.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("{") and stripped.endswith("}")):
                continue
            with contextlib.suppress(json.JSONDecodeError):
                obj = json.loads(stripped)
                if isinstance(obj, dict) and "verdict" in obj:
                    return str(obj["verdict"])
        return None

    @property
    def verdict(self) -> SlicePlanVerdict:
        """Map the CLI output onto the user-observable verdict, per mode.

        PLAIN mode -- the pre-existing heading-form contract: exit 0 ->
        ACCEPTED, any non-zero -> MALFORMED_WAVE_HEADING (the only rejection
        the plain check can produce). This branch reads the EXIT CODE, the
        stable contract the plain CLI has on master and keeps forever -- so the
        no-regression pin scenario is green against the real master CLI.

        REQUIRE_SLICE_PLAN mode -- the slice-06 ``--format=json`` contract:
        the verdict is the stable ``verdict`` token of the single emitted JSON
        object (one of the closed set in ``_VERDICT_TOKEN``). This reads a
        MACHINE token, never free-text stdout substrings, so a crafter that
        phrases its diagnostic differently cannot cause a silent
        misclassification.

          - No ``verdict`` token at all -> UNRECOGNISED_INVOCATION: the CLI did
            not produce structured output. On master the ``--require-slice-plan``
            / ``--format=json`` flags are unknown, so EVERY --require-slice-plan
            scenario lands here -- the unambiguous regression RED signal.
          - An off-contract token (a JSON ``verdict`` whose value is NOT in the
            closed set) is a contract violation -> ``ValueError``, failing the
            test loudly. The mapping never silently defaults.
        """
        if self.mode is CheckMode.PLAIN:
            if self.exit_code == 0:
                return SlicePlanVerdict.ACCEPTED
            return SlicePlanVerdict.MALFORMED_WAVE_HEADING
        token = self._verdict_token
        if token is None:
            return SlicePlanVerdict.UNRECOGNISED_INVOCATION
        if token not in _VERDICT_TOKEN:
            raise ValueError(
                f"slice-06 CLI emitted an off-contract verdict token {token!r}; "
                f"expected one of {sorted(_VERDICT_TOKEN)}"
            )
        return _VERDICT_TOKEN[token]


@dataclass
class SlicePlanValidationComposition:
    """Production-wired composition root for the slice-plan-validation slice.

    ``repo_dir`` is a real tmp_path directory acting as the repository root.
    The feature-delta is provisioned via ``provision_feature_delta`` so each
    scenario builds exactly the slice-plan shape it needs; the validator CLI is
    then invoked through its argv entry point against that file.
    """

    repo_dir: Path
    feature_id: FeatureId = field(default=FeatureId("atdd-pure-demo"))

    # --- paths ---------------------------------------------------------------

    @property
    def _feature_dir(self) -> Path:
        return self.repo_dir / "docs" / "feature" / self.feature_id

    @property
    def feature_delta_path(self) -> Path:
        return self._feature_dir / "feature-delta.md"

    # --- Given: repo ---------------------------------------------------------

    def create_feature(self, feature_id: FeatureId) -> None:
        """Create the feature directory skeleton."""
        self.feature_id = feature_id
        self._feature_dir.mkdir(parents=True, exist_ok=True)

    # --- Given: feature-delta + slice plan -----------------------------------

    def provision_feature_delta(self, shape: SlicePlanShape) -> None:
        """Write the feature-delta with a slice plan of the requested shape."""
        builder = _FEATURE_DELTA_BUILDERS[shape]
        builder(self)

    def _write(self, body: str) -> None:
        """Write the feature-delta document body."""
        self.feature_delta_path.write_text(body, encoding="utf-8")

    # --- When: run the validator ---------------------------------------------

    def run_check(self, mode: CheckMode) -> ValidationResult:
        """Invoke the production validate-feature-delta CLI via its argv entry.

        ``CheckMode.PLAIN`` invokes the heading-form-only contract (one path
        argument); ``CheckMode.REQUIRE_SLICE_PLAN`` adds the
        ``--require-slice-plan --format=json`` flags introduced by slice-06,
        so the verdict is read from a structured ``verdict`` token.
        """
        argv = _ARGV_BY_MODE[mode](self.feature_delta_path)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            exit_code = validate_feature_delta_main(argv)
        return ValidationResult(
            mode=mode, exit_code=exit_code, output=buffer.getvalue()
        )

    # --- universe ------------------------------------------------------------

    def capture_universe(self) -> dict[str, object]:
        """Port-exposed observable snapshot for assert_state_delta (Mandate 8).

        The validator has a pure-function contract: it reads the feature-delta
        and MUST NOT mutate it. The universe is the feature-delta's existence
        and bytes -- the state-delta guard proves the read-only contract.
        """
        return {
            "feature_delta.exists": self.feature_delta_path.exists(),
            "feature_delta.bytes": (
                self.feature_delta_path.read_bytes()
                if self.feature_delta_path.exists()
                else None
            ),
        }


# --- argv builders ----------------------------------------------------------
# Each builder keeps `run_check` a single typed dispatch + a single CLI call
# (Mandate-12 criterion 3: no control flow in the service method body).


def _argv_plain(path: Path) -> list[str]:
    return [str(path)]


def _argv_require_slice_plan(path: Path) -> list[str]:
    # slice-06 contract: --require-slice-plan is paired with --format=json so
    # the verdict is read from a structured `verdict` token, not free text.
    return ["--require-slice-plan", "--format=json", str(path)]


_ARGV_BY_MODE: dict[CheckMode, Callable[[Path], list[str]]] = {
    CheckMode.PLAIN: _argv_plain,
    CheckMode.REQUIRE_SLICE_PLAN: _argv_require_slice_plan,
}


# --- feature-delta fixture builders -----------------------------------------
# Module-level dispatch keeps each Given step body a single typed lookup + a
# single composition call (Mandate-12 criterion 3: no control flow in steps).


def _slice_plan_section(header: str, separator: str, rows: str) -> str:
    """Assemble a `[REF] Slice Plan` section from header / separator / rows."""
    return f"## Wave: DISCUSS / [REF] Slice Plan\n\n{header}\n{separator}\n{rows}"


def _doc(*sections: str) -> str:
    """Assemble a feature-delta document body from its sections."""
    return "# Feature Delta: slice-plan validation fixture\n\n" + "\n\n".join(sections)


def _build_well_formed(comp: SlicePlanValidationComposition) -> None:
    comp._write(
        _doc(
            _slice_plan_section(
                "| Slice | Value statement | Status | Annotation | Justification |",
                "|-------|-----------------|--------|------------|---------------|",
                f"{_WS_ROW}\n| slice-02 | Operator applies a plan | pending | | |",
            )
        )
    )


def _build_many_rows(comp: SlicePlanValidationComposition) -> None:
    rows = "\n".join(
        f"| slice-{n:02d} | Operator value {n} | pending | | |" for n in range(2, 13)
    )
    comp._write(
        _doc(
            _slice_plan_section(
                "| Slice | Value statement | Status | Annotation | Justification |",
                "|-------|-----------------|--------|------------|---------------|",
                f"{_WS_ROW}\n{rows}",
            )
        )
    )


def _build_section_absent(comp: SlicePlanValidationComposition) -> None:
    # A feature-delta with a valid wave heading but NO slice-plan section.
    comp._write(
        _doc(
            "## Wave: DISCUSS / [REF] Inherited commitments\n\n"
            "| Origin | Commitment | DDD | Impact |\n"
            "|--------|------------|-----|--------|\n"
            "| n/a | a commitment | n/a | a substantive consequence here |"
        )
    )


def _build_four_columns(comp: SlicePlanValidationComposition) -> None:
    # The section is present, but the table drops the Justification column.
    comp._write(
        _doc(
            _slice_plan_section(
                "| Slice | Value statement | Status | Annotation |",
                "|-------|-----------------|--------|------------|",
                "| slice-01 | Operator previews a plan | pending | |",
            )
        )
    )


def _build_header_only(comp: SlicePlanValidationComposition) -> None:
    # Five-column header + separator, but ZERO slice rows -- an empty plan.
    comp._write(
        _doc(
            "## Wave: DISCUSS / [REF] Slice Plan\n\n"
            "| Slice | Value statement | Status | Annotation | Justification |\n"
            "|-------|-----------------|--------|------------|---------------|"
        )
    )


def _build_columns_reordered(comp: SlicePlanValidationComposition) -> None:
    # All five columns present but in a different order. ADR-028 D2 (L137)
    # mandates "Five columns, fixed order" -- a re-order violates that fixed
    # contract, so the validator rejects this as a malformed slice plan.
    comp._write(
        _doc(
            _slice_plan_section(
                "| Status | Slice | Justification | Value statement | Annotation |",
                "|--------|-------|---------------|-----------------|------------|",
                "| pending | slice-01 | thinnest vertical | Operator previews | "
                "@walking-skeleton |",
            )
        )
    )


def _build_malformed_heading(comp: SlicePlanValidationComposition) -> None:
    # A well-formed slice plan, but a SECOND wave heading omits the [REF|WHY|HOW]
    # token -- the pre-existing heading-form check must still fire.
    comp._write(
        _doc(
            "## Wave: DESIGN Architecture overview",
            _slice_plan_section(
                "| Slice | Value statement | Status | Annotation | Justification |",
                "|-------|-----------------|--------|------------|---------------|",
                _WS_ROW,
            ),
        )
    )


_FEATURE_DELTA_BUILDERS: dict[
    SlicePlanShape, Callable[[SlicePlanValidationComposition], None]
] = {
    SlicePlanShape.WELL_FORMED: _build_well_formed,
    SlicePlanShape.MANY_ROWS: _build_many_rows,
    SlicePlanShape.SECTION_ABSENT: _build_section_absent,
    SlicePlanShape.FOUR_COLUMNS: _build_four_columns,
    SlicePlanShape.HEADER_ONLY: _build_header_only,
    SlicePlanShape.COLUMNS_REORDERED: _build_columns_reordered,
    SlicePlanShape.MALFORMED_HEADING: _build_malformed_heading,
}
