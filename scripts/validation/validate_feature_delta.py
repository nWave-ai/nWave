"""validate_feature_delta — schema validator for lean feature-delta.md (C14).

Dev/CI-only validator (NOT shipped to end users). Two validation modes:

- **Plain mode** (no flag) — enforces D2 schema-typed section headings: every
  `## Wave: <NAME> / [<TYPE>] <Section>` heading must declare a TYPE token in
  {REF, WHY, HOW}. Non-Wave `##` headings are out of scope.
- **`--require-slice-plan` mode** (slice-06, ADR-028 D2 / D2-bis, ADR-029 D3) —
  additionally asserts the `## Wave: DISCUSS / [REF] Slice Plan` section is
  present and its table carries the five required columns in fixed order. Used
  by the Product Owner at DISCUSS authoring time so a missing or malformed
  slice plan is caught before the feature-delta flows downstream.

CLI contract:
- Plain mode (AC-5.c): exit 0 on a well-formed lean feature-delta.md;
  exit non-zero with an explicit list of malformed headings otherwise.
- `--require-slice-plan --format=json` mode: emit a single JSON object to
  stdout carrying a stable `"verdict"` field whose value is exactly one of the
  closed token set {accepted, missing-slice-plan, malformed-slice-plan,
  malformed-wave-heading}; exit 0 on `accepted`, non-zero on any rejection.

Architecture:
- Pure functional core (`validate_feature_delta_content`,
  `validate_slice_plan_content`) — no I/O.
- Thin CLI shell (`main`) — reads file, calls pure functions, prints, returns
  exit code.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Domain types — pure data carriers
# ---------------------------------------------------------------------------

#: Tokens accepted in the `[<TYPE>]` slot of a Wave heading per D2.
ALLOWED_TYPE_TOKENS: frozenset[str] = frozenset({"REF", "WHY", "HOW"})

#: The five required slice-plan columns, in the D2 fixed order (ADR-028 D2 L137:
#: "Five columns, fixed order"). A re-order violates the fixed-order contract.
SLICE_PLAN_COLUMNS: tuple[str, ...] = (
    "Slice",
    "Value statement",
    "Status",
    "Annotation",
    "Justification",
)

#: The closed `verdict` token set emitted under --require-slice-plan
#: --format=json. Each token is a STRUCTURED contract — the AT reads the token,
#: never a free-text stdout substring.
VERDICT_ACCEPTED = "accepted"
VERDICT_MISSING_SLICE_PLAN = "missing-slice-plan"
VERDICT_MALFORMED_SLICE_PLAN = "malformed-slice-plan"
VERDICT_MALFORMED_WAVE_HEADING = "malformed-wave-heading"

#: Match a Wave-prefixed `##` heading. Captures (wave_name, type_token, tail).
#: Anchored on the schema separator ` / ` so non-conforming headings still
#: parse but flag a violation.
_WAVE_HEADING_RE = re.compile(
    r"^##\s+Wave:\s+(?P<wave>[A-Za-z0-9_\- ]+?)\s*/\s*"
    r"\[(?P<type>[^\]]+)\]\s+(?P<section>.+?)\s*$"
)

#: Match any heading that starts with `## Wave:` — used to detect Wave headings
#: that are malformed AND lack the schema separator entirely.
_WAVE_PREFIX_RE = re.compile(r"^##\s+Wave:\s")

#: Match the canonical slice-plan section heading (ADR-028 D2 L133).
_SLICE_PLAN_HEADING_RE = re.compile(
    r"^##\s+Wave:\s+DISCUSS\s*/\s*\[REF\]\s+Slice\s+Plan\s*$"
)

#: Match any `##` markdown heading (level-2 only, not `###` or deeper).
_H2_RE = re.compile(r"^##\s+(?!#)(?P<text>.+?)\s*$")


class Offender(NamedTuple):
    """A heading that violates the D2 schema."""

    line: int
    heading: str
    reason: str


class ValidationResult(NamedTuple):
    """Outcome of validating one feature-delta.md."""

    is_valid: bool
    offenders: list[Offender]
    wave_section_count: int


class SlicePlanResult(NamedTuple):
    """Outcome of the --require-slice-plan structural slice-plan check.

    `verdict` is one of the closed token set; `detail` is a human-readable
    diagnostic naming the cause (for the JSON payload + plain-text rendering).
    """

    verdict: str
    detail: str


# ---------------------------------------------------------------------------
# Pure core — heading-form validation
# ---------------------------------------------------------------------------


def _classify_wave_heading(line_no: int, raw_text: str) -> Offender | None:
    """Validate one Wave heading. Pure.

    Args:
        line_no: 1-based line number for diagnostics.
        raw_text: stripped heading line, including the leading `## `.

    Returns:
        None if the heading conforms to the schema; an Offender otherwise.
    """
    match = _WAVE_HEADING_RE.match(raw_text)
    if match is None:
        return Offender(
            line=line_no,
            heading=raw_text,
            reason=(
                "missing schema prefix; expected "
                "'## Wave: <NAME> / [REF|WHY|HOW] <Section>'"
            ),
        )
    type_token = match.group("type")
    if type_token not in ALLOWED_TYPE_TOKENS:
        return Offender(
            line=line_no,
            heading=raw_text,
            reason=(
                f"invalid type token '[{type_token}]'; "
                f"expected one of {sorted(ALLOWED_TYPE_TOKENS)}"
            ),
        )
    return None


def validate_feature_delta_content(content: str) -> ValidationResult:
    """Validate a feature-delta.md document body. Pure function.

    Walks each line; for every `## Wave:` heading delegates to
    `_classify_wave_heading`. Other H2 headings are ignored (meta sections
    such as `## Expansions requested` are out-of-scope per scope of D2).

    Args:
        content: file body (UTF-8 text).

    Returns:
        ValidationResult with `is_valid` true iff no offenders were found.
    """
    offenders: list[Offender] = []
    wave_count = 0

    for idx, line in enumerate(content.splitlines(), start=1):
        if not _WAVE_PREFIX_RE.match(line):
            continue
        wave_count += 1
        offender = _classify_wave_heading(idx, line.rstrip())
        if offender is not None:
            offenders.append(offender)

    return ValidationResult(
        is_valid=not offenders,
        offenders=offenders,
        wave_section_count=wave_count,
    )


# ---------------------------------------------------------------------------
# Pure core — slice-plan structural validation (slice-06)
# ---------------------------------------------------------------------------


def _parse_table_cells(row: str) -> list[str]:
    """Split a GFM table row into its trimmed cell values. Pure.

    A GFM row is `| a | b | c |`; the leading and trailing pipes produce empty
    edge fields which are dropped.
    """
    parts = [cell.strip() for cell in row.strip().split("|")]
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return parts


def _is_separator_row(row: str) -> bool:
    """True if `row` is a GFM table separator (`|---|---|`)."""
    cells = _parse_table_cells(row)
    return bool(cells) and all(
        set(cell) <= {"-", ":"} and "-" in cell for cell in cells
    )


def _slice_plan_table_rows(content: str) -> list[str] | None:
    """Extract the slice-plan table's raw rows. Pure.

    Locates the single `## Wave: DISCUSS / [REF] Slice Plan` heading and
    collects the first GFM table beneath it — non-blank lines starting with
    `|`, taken until the first blank line or next `##` heading.

    Returns:
        The list of raw table rows (header, separator, then slice rows), or
        None when the slice-plan heading is absent.
    """
    lines = content.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if _SLICE_PLAN_HEADING_RE.match(line.rstrip()):
            start = idx + 1
            break
    if start is None:
        return None

    rows: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("##"):
            break
        if not stripped:
            if rows:
                break
            continue
        if stripped.startswith("|"):
            rows.append(stripped)
        elif rows:
            break
    return rows


def validate_slice_plan_content(content: str) -> SlicePlanResult:
    """Structurally validate the slice-plan section. Pure function.

    Runs the heading-form check first (a malformed wave heading anywhere is
    reported as `malformed-wave-heading` regardless of slice-plan shape), then
    the slice-plan structural check:

    - section absent                        -> missing-slice-plan
    - table column header not the D2 fixed   -> malformed-slice-plan
      five columns (wrong count or reordered)
    - header + separator but zero slice rows -> malformed-slice-plan
    - well-formed five-column table, >=1 row -> accepted

    Args:
        content: feature-delta.md body (UTF-8 text).

    Returns:
        SlicePlanResult carrying the closed-set verdict token + a diagnostic.
    """
    heading_result = validate_feature_delta_content(content)
    if not heading_result.is_valid:
        first = heading_result.offenders[0]
        return SlicePlanResult(
            verdict=VERDICT_MALFORMED_WAVE_HEADING,
            detail=(
                f"malformed wave heading at line {first.line}: "
                f"{first.heading} - {first.reason}"
            ),
        )

    rows = _slice_plan_table_rows(content)
    if rows is None:
        return SlicePlanResult(
            verdict=VERDICT_MISSING_SLICE_PLAN,
            detail=(
                "no '## Wave: DISCUSS / [REF] Slice Plan' section found (ADR-028 D2)"
            ),
        )

    header_cells = _parse_table_cells(rows[0]) if rows else []
    if tuple(header_cells) != SLICE_PLAN_COLUMNS:
        return SlicePlanResult(
            verdict=VERDICT_MALFORMED_SLICE_PLAN,
            detail=(
                f"slice-plan table columns {header_cells} do not match the "
                f"D2 fixed five-column header {list(SLICE_PLAN_COLUMNS)}"
            ),
        )

    slice_rows = [row for row in rows[1:] if not _is_separator_row(row)]
    if not slice_rows:
        return SlicePlanResult(
            verdict=VERDICT_MALFORMED_SLICE_PLAN,
            detail="slice-plan table has its header but zero slice rows",
        )

    return SlicePlanResult(
        verdict=VERDICT_ACCEPTED,
        detail=f"slice plan is well formed; {len(slice_rows)} slice rows",
    )


# ---------------------------------------------------------------------------
# Thin CLI shell — only side effect boundary
# ---------------------------------------------------------------------------


def _format_success(result: ValidationResult) -> str:
    return f"Feature delta is valid. {result.wave_section_count} wave sections checked."


def _format_failure(result: ValidationResult) -> str:
    lines = [f"Feature delta has {len(result.offenders)} malformed headings:"]
    for offender in result.offenders:
        lines.append(f"  line {offender.line}: {offender.heading} - {offender.reason}")
    return "\n".join(lines)


def validate_feature_delta(file_path: Path) -> ValidationResult:
    """Read `file_path` and validate its content. Thin I/O wrapper.

    Args:
        file_path: Path to a feature-delta.md file.

    Returns:
        ValidationResult.
    """
    content = file_path.read_text(encoding="utf-8")
    return validate_feature_delta_content(content)


_USAGE = (
    "usage: validate_feature_delta.py [--require-slice-plan] [--format=json] "
    "<path-to-feature-delta.md>"
)


class _ParsedArgs(NamedTuple):
    """Parsed CLI arguments."""

    path: str
    require_slice_plan: bool
    json_format: bool


def _parse_args(args: list[str]) -> _ParsedArgs | None:
    """Parse the CLI argument list. Returns None on malformed invocation.

    Accepts the optional flags `--require-slice-plan` and `--format=json` in
    any order, plus exactly one positional path argument. The plain-mode
    contract (a lone path argument) is preserved.
    """
    require_slice_plan = False
    json_format = False
    positionals: list[str] = []
    for arg in args:
        if arg == "--require-slice-plan":
            require_slice_plan = True
        elif arg == "--format=json":
            json_format = True
        elif arg.startswith("-"):
            return None
        else:
            positionals.append(arg)
    if len(positionals) != 1:
        return None
    return _ParsedArgs(
        path=positionals[0],
        require_slice_plan=require_slice_plan,
        json_format=json_format,
    )


def _run_plain(target: Path) -> int:
    """Run the heading-form-only check. Plain-text output, exit 0/1."""
    result = validate_feature_delta(target)
    if result.is_valid:
        print(_format_success(result))
        return 0
    print(_format_failure(result))
    return 1


def _run_require_slice_plan(target: Path, json_format: bool) -> int:
    """Run the structural slice-plan check (slice-06).

    Emits a single JSON object carrying the closed-set `verdict` token (when
    `--format=json` is set) and returns exit 0 on `accepted`, 1 on rejection.
    """
    content = target.read_text(encoding="utf-8")
    result = validate_slice_plan_content(content)
    if json_format:
        print(json.dumps({"verdict": result.verdict, "detail": result.detail}))
    else:
        print(f"{result.verdict}: {result.detail}")
    return 0 if result.verdict == VERDICT_ACCEPTED else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry: `validate_feature_delta.py [flags] <path-to-feature-delta.md>`.

    Args:
        argv: optional argument list (defaults to `sys.argv[1:]`).

    Returns:
        0 on success, 1 on any malformed heading / malformed slice plan / I/O
        error.
    """
    args = sys.argv[1:] if argv is None else argv
    parsed = _parse_args(args)
    if parsed is None:
        print(_USAGE, file=sys.stderr)
        return 1

    target = Path(parsed.path)
    if not target.is_file():
        print(f"error: {target} is not a file", file=sys.stderr)
        return 1

    if parsed.require_slice_plan:
        return _run_require_slice_plan(target, parsed.json_format)
    return _run_plain(target)


if __name__ == "__main__":
    raise SystemExit(main())
