"""Carpaccio slice gate CLI -- the ATDD-pure DELIVER entry gate.

ADR-028 D2-bis (carpaccio assertions 1-4) + ADR-029 D5 (assertion 5, the
AT-review gate). Runs as a DES ``entry_gate`` before ``A_GREEN_ATS``: a slice
reaches implementation only when BOTH halves clear -- the carpaccio
decomposition check (the slice is a thin enough vertical) AND the AT-review
check (the slice's acceptance tests were reviewed and approved).

Modelled on ``scripts/cli/cohort_classifier.py``: single-file core CLI,
single-line JSON output, explicit exit codes, pure-function -- the gate reads
the feature-delta + ``.feature`` files + the AT-completion ledger and returns a
verdict (exit code + JSON); it performs NO filesystem mutation.

Exit codes:
    0  -- the slice is cleared to enter implementation
    1  -- the feature-delta or its ``[REF] Slice Plan`` section is absent
    2  -- malformed input (the slice-plan table OR a ``.feature`` slice tag);
          the emitted JSON ``cause`` field names which input to repair
    44 -- CARPACCIO_SLICE_TOO_LARGE: oversized / coverage / ordering violation
    45 -- AT_REVIEW_NOT_APPROVED: assertion 5 failed (one of six closed reasons)
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# Default carpaccio slice-size ceiling when .nwave/config.yaml omits it.
_DEFAULT_SLICE_MAX = 3

# Reviewer signing-key precedence -- mirrors verify_commit_trailers.py.
_SIGNING_KEY_ENV = "NWAVE_REVIEWER_SIGNING_KEY"
_SIGNING_KEY_FILE = ".nwave/secrets/reviewer-signing.key"

# The seven HMAC-signed fields of an ATReviewVerdict record (ADR-029 D5 / B1).
_SIGNED_FIELDS = (
    "schema_version",
    "slice_id",
    "verdict",
    "reviewer_agent_id",
    "at_ids",
    "at_content_hash",
    "timestamp",
)

_SLICE_PLAN_HEADING_RE = re.compile(
    r"^##\s+Wave:\s+DISCUSS\s+/\s+\[REF\]\s+Slice Plan\s*$"
)
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_SLICE_ID_RE = re.compile(r"^slice-\d+$")
_SLICE_TAG_RE = re.compile(r"@(slice-\d+)\b")
_COUPLED_TAG_RE = re.compile(r"@coupled\b")
_WALKING_SKELETON_RE = re.compile(r"@walking-skeleton|@walking_skeleton")
_ANNOTATION_ESCAPE_RE = re.compile(
    r"@coupled|@walking-skeleton|@walking_skeleton|@infrastructure"
)


class GateError(Exception):
    """A gate verdict carrying a non-zero exit code and a JSON payload.

    Raised by the parse/assertion helpers and caught by ``main`` so each
    failure path emits exactly one single-line JSON object before exiting.
    """

    def __init__(self, exit_code: int, payload: dict[str, object]) -> None:
        super().__init__(payload.get("error", payload.get("event", "gate error")))
        self.exit_code = exit_code
        self.payload = payload


@dataclass(frozen=True)
class SlicePlanRow:
    """One parsed row of the ``[REF] Slice Plan`` table."""

    slice_id: str
    value_statement: str
    status: str
    annotation: str
    justification: str


@dataclass(frozen=True)
class SlicePlan:
    """The parsed ``[REF] Slice Plan`` table -- ordered slice rows."""

    rows: tuple[SlicePlanRow, ...]

    def row_for(self, slice_id: str) -> SlicePlanRow | None:
        for row in self.rows:
            if row.slice_id == slice_id:
                return row
        return None


# ---------------------------------------------------------------------------
# Repo / path resolution
# ---------------------------------------------------------------------------


def _repo_root(override: str | None) -> Path:
    if override:
        return Path(override)
    env = os.environ.get("NWAVE_REPO_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _feature_delta_path(repo: Path, feature_id: str) -> Path:
    return repo / "docs" / "feature" / feature_id / "feature-delta.md"


def _legacy_acceptance_dir(repo: Path, feature_id: str) -> Path:
    """The pre-F-04 hardcoded AT directory for ``feature_id``.

    A ``.feature`` file under ``tests/scripts/cli/{feature_id}/acceptance``
    is feature-scoped by its directory name, so it is bound to ``feature_id``
    even when it carries no file-level ``@feature-`` tag.
    """
    return repo / "tests" / "scripts" / "cli" / feature_id / "acceptance"


def _feature_tag_files(repo: Path, feature_id: str) -> list[Path]:
    """Resolve every ``.feature`` file authored for ``feature_id``.

    F-04 (atdd-pure-dogfooding-friction-2026-05-20.md): the gate must find a
    feature's ``.feature`` files wherever DISTILL placed them, not only under
    a hardcoded ``tests/scripts/cli/{feature_id}/acceptance`` path. A file is
    bound to the feature when it self-identifies with a file-level
    ``@feature-{feature_id}`` tag preceding its ``Feature:`` header, OR it
    lives under the legacy feature-scoped acceptance directory. The legacy
    path stays a source -- it is no longer the ONLY source.
    """
    tests_dir = repo / "tests"
    if not tests_dir.is_dir():
        return []
    wanted = f"@feature-{feature_id}"
    legacy_dir = _legacy_acceptance_dir(repo, feature_id)
    matched: set[Path] = set()
    for path in tests_dir.rglob("*.feature"):
        if wanted in _file_feature_tags(path) or legacy_dir in path.parents:
            matched.add(path)
    return sorted(matched)


def _file_feature_tags(path: Path) -> tuple[str, ...]:
    """Collect the file-level ``@`` tags appearing before the ``Feature:`` line."""
    tags: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            # Gherkin comment line -- may precede the file-level tag block.
            continue
        if stripped.startswith("@"):
            tags.extend(stripped.split())
            continue
        if stripped.startswith("Feature:"):
            break
        # Any other non-blank content before Feature: -- stop scanning tags.
        break
    return tuple(tags)


def _ledger_path(repo: Path, feature_id: str) -> Path:
    return repo / ".nwave" / "telemetry" / "atdd-pure" / f"{feature_id}.jsonl"


def _config_slice_max(repo: Path) -> int:
    """Read ``atdd_pure.carpaccio_slice_max`` from ``.nwave/config.yaml``."""
    config_path = repo / ".nwave" / "config.yaml"
    if not config_path.is_file():
        return _DEFAULT_SLICE_MAX
    try:
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return _DEFAULT_SLICE_MAX
    value = (data.get("atdd_pure") or {}).get("carpaccio_slice_max")
    if isinstance(value, int) and value > 0:
        return value
    return _DEFAULT_SLICE_MAX


# ---------------------------------------------------------------------------
# Slice-plan table parsing (ADR-028 D2-bis)
# ---------------------------------------------------------------------------


def _split_table_cells(line: str) -> list[str]:
    """Split a GFM table row into trimmed cells, dropping the outer pipes."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_slice_plan(feature_delta_text: str) -> SlicePlan:
    """Parse the ``[REF] Slice Plan`` table out of a feature-delta.

    Raises ``GateError`` exit 1 when the section heading is absent, exit 2
    when the table is malformed (wrong column count, bad slice identifier,
    duplicate slice id).
    """
    lines = feature_delta_text.splitlines()
    heading_index = next(
        (i for i, line in enumerate(lines) if _SLICE_PLAN_HEADING_RE.match(line)),
        None,
    )
    if heading_index is None:
        raise GateError(
            1,
            {
                "event": "SlicePlanSectionMissing",
                "error": "feature-delta has no '[REF] Slice Plan' section",
            },
        )
    table_rows = _collect_table_rows(lines, heading_index + 1)
    if len(table_rows) < 2:
        raise _malformed_table("the slice-plan table has no data rows")
    return _build_slice_plan(table_rows[2:])


def _collect_table_rows(lines: list[str], start: int) -> list[str]:
    """Collect the contiguous GFM table block after the section heading."""
    rows: list[str] = []
    started = False
    for line in lines[start:]:
        if _TABLE_ROW_RE.match(line):
            started = True
            rows.append(line)
            continue
        if started:
            break
    return rows


def _build_slice_plan(data_rows: list[str]) -> SlicePlan:
    """Validate + build slice rows from the table data rows (exit 2 on error)."""
    rows: list[SlicePlanRow] = []
    seen: set[str] = set()
    for raw in data_rows:
        cells = _split_table_cells(raw)
        if len(cells) != 5:
            raise _malformed_table(
                f"slice-plan row must have 5 columns, found {len(cells)}: {raw!r}"
            )
        slice_id = cells[0]
        if not _SLICE_ID_RE.match(slice_id):
            raise _malformed_table(
                f"slice-plan row identifier must match 'slice-NN': {slice_id!r}"
            )
        if slice_id in seen:
            raise _malformed_table(f"duplicate slice id in slice plan: {slice_id!r}")
        seen.add(slice_id)
        rows.append(
            SlicePlanRow(
                slice_id=slice_id,
                value_statement=cells[1],
                status=cells[2],
                annotation=cells[3],
                justification=cells[4],
            )
        )
    if not rows:
        raise _malformed_table("the slice-plan table has no slice rows")
    return SlicePlan(rows=tuple(rows))


def _malformed_table(detail: str) -> GateError:
    return GateError(
        2,
        {
            "event": "MalformedInput",
            "cause": "the slice-plan table",
            "error": detail,
        },
    )


def _malformed_feature_tag(detail: str) -> GateError:
    return GateError(
        2,
        {
            "event": "MalformedInput",
            "cause": "a .feature slice tag",
            "error": detail,
        },
    )


# ---------------------------------------------------------------------------
# .feature scenario parsing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """One parsed ``.feature`` scenario: its slice tags + its normalized body."""

    slice_tags: tuple[str, ...]
    has_coupled_tag: bool
    normalized_body: str


def _read_feature_files(repo: Path, feature_id: str) -> list[str]:
    """Read every ``.feature`` file self-identifying with ``feature_id``."""
    return [
        path.read_text(encoding="utf-8", errors="replace")
        for path in _feature_tag_files(repo, feature_id)
    ]


def parse_scenarios(feature_texts: list[str]) -> list[Scenario]:
    """Parse every ``Scenario`` block across the slice's ``.feature`` files."""
    scenarios: list[Scenario] = []
    for text in feature_texts:
        scenarios.extend(_parse_scenarios_in_text(text))
    return scenarios


def _parse_scenarios_in_text(text: str) -> list[Scenario]:
    lines = text.splitlines()
    scenarios: list[Scenario] = []
    pending_tags: list[str] = []
    block: list[str] | None = None
    block_tags: list[str] = []

    def flush() -> None:
        if block is not None:
            scenarios.append(_make_scenario(block_tags, block))

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("@"):
            pending_tags.append(stripped)
            continue
        if stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:"):
            flush()
            block = []
            block_tags = list(pending_tags)
            pending_tags = []
            continue
        if stripped.startswith("Feature:"):
            pending_tags = []
            continue
        if block is not None:
            block.append(line)
    flush()
    return scenarios


def _make_scenario(tag_lines: list[str], body_lines: list[str]) -> Scenario:
    tag_text = " ".join(tag_lines)
    slice_tags = tuple(_SLICE_TAG_RE.findall(tag_text))
    has_coupled = bool(_COUPLED_TAG_RE.search(tag_text))
    normalized = _normalize_body(body_lines)
    return Scenario(
        slice_tags=slice_tags,
        has_coupled_tag=has_coupled,
        normalized_body=normalized,
    )


def _normalize_body(body_lines: list[str]) -> str:
    """Normalize a scenario body: strip per line, drop blanks, lowercase.

    Tag lines are already excluded by the parser. Per ADR-029 D5 Hole-fix:
    a pure re-tag does not churn the hash, any Given/When/Then edit does.
    """
    cleaned = [line.strip().lower() for line in body_lines if line.strip()]
    return "\n".join(cleaned)


# ---------------------------------------------------------------------------
# Carpaccio assertions 1-4 (ADR-028 D2-bis)
# ---------------------------------------------------------------------------


def check_carpaccio(
    plan: SlicePlan,
    scenarios: list[Scenario],
    entering_slice: str,
    slice_max: int,
) -> dict[str, object] | None:
    """Run carpaccio assertions 1-4. Raises ``GateError`` on a violation.

    Returns a non-None dict only to surface the ``CoupledSliceAccepted``
    event when an over-N coupled slice with a justification is accepted.
    """
    if plan.row_for(entering_slice) is None:
        raise GateError(
            44,
            {
                "event": "CARPACCIO_SLICE_TOO_LARGE",
                "error": (
                    f"entering slice {entering_slice!r} has no row in the slice plan"
                ),
                "instruction": (
                    "add a slice-plan row for the entering slice, or re-slice"
                ),
            },
        )
    _check_total_coverage(plan, scenarios)
    if not _slice_scenarios(scenarios, entering_slice):
        raise _at_review_rejection("no-scenarios-for-slice", entering_slice)
    _check_walking_skeleton_first(plan)
    _check_value_annotation(plan)
    return _check_slice_size(plan, scenarios, entering_slice, slice_max)


def _slice_scenarios(scenarios: list[Scenario], slice_id: str) -> list[Scenario]:
    return [s for s in scenarios if slice_id in s.slice_tags]


def _check_total_coverage(plan: SlicePlan, scenarios: list[Scenario]) -> None:
    """Assertion 2: every authored scenario carries exactly one @slice-NN tag."""
    plan_ids = {row.slice_id for row in plan.rows}
    for scenario in scenarios:
        tag_count = len(scenario.slice_tags)
        if tag_count == 0:
            raise GateError(
                44,
                {
                    "event": "CARPACCIO_SLICE_TOO_LARGE",
                    "error": (
                        "an authored scenario carries no @slice-NN tag "
                        "(incremental total-coverage violation)"
                    ),
                    "instruction": (
                        "tag every authored scenario with exactly one @slice-NN"
                    ),
                },
            )
        if tag_count > 1:
            raise GateError(
                44,
                {
                    "event": "CARPACCIO_SLICE_TOO_LARGE",
                    "error": (
                        "an authored scenario carries multiple @slice-NN tags "
                        f"({sorted(scenario.slice_tags)})"
                    ),
                    "instruction": "give each scenario exactly one @slice-NN tag",
                },
            )
        tag = scenario.slice_tags[0]
        if tag not in plan_ids:
            raise _malformed_feature_tag(
                f"a .feature scenario carries @{tag} with no matching slice-plan row"
            )


def _check_walking_skeleton_first(plan: SlicePlan) -> None:
    """Assertion 3: a @walking-skeleton slice must be the first plan row."""
    ws_index = next(
        (
            i
            for i, row in enumerate(plan.rows)
            if _WALKING_SKELETON_RE.search(row.annotation)
        ),
        None,
    )
    if ws_index is not None and ws_index != 0:
        raise GateError(
            44,
            {
                "event": "CARPACCIO_SLICE_TOO_LARGE",
                "error": (
                    "the @walking-skeleton slice is not ordered first "
                    f"(found at row {ws_index + 1})"
                ),
                "instruction": "order the @walking-skeleton slice first in the plan",
            },
        )


def _check_value_annotation(plan: SlicePlan) -> None:
    """Assertion 4: an annotated escape row must record a justification."""
    for row in plan.rows:
        if _ANNOTATION_ESCAPE_RE.search(row.annotation) and not row.justification:
            raise GateError(
                44,
                {
                    "event": "CARPACCIO_SLICE_TOO_LARGE",
                    "error": (
                        f"slice {row.slice_id} carries annotation "
                        f"{row.annotation!r} but records no justification"
                    ),
                    "instruction": "record a justification for the annotated slice",
                },
            )


def _check_slice_size(
    plan: SlicePlan,
    scenarios: list[Scenario],
    entering_slice: str,
    slice_max: int,
) -> dict[str, object] | None:
    """Assertion 1: slice size <= N unless a coupled-AT-group escape applies.

    The only size escape (ADR-028 D2) is a coupled AT group: every scenario
    in the slice carries a ``@coupled`` tag AND the plan row records a
    coupling justification. A plain ``@walking-skeleton`` / ``@infrastructure``
    annotation does NOT lift the size ceiling -- it governs ordering and the
    value-annotation check, not slice size.
    """
    slice_scenarios = _slice_scenarios(scenarios, entering_slice)
    at_count = len(slice_scenarios)
    if at_count <= slice_max:
        return None
    row = plan.row_for(entering_slice)
    assert row is not None  # guaranteed by check_carpaccio precondition
    all_coupled = bool(slice_scenarios) and all(
        s.has_coupled_tag for s in slice_scenarios
    )
    if all_coupled and row.justification:
        return {
            "event": "CoupledSliceAccepted",
            "slice_id": entering_slice,
            "at_count": at_count,
        }
    raise GateError(
        44,
        {
            "event": "CARPACCIO_SLICE_TOO_LARGE",
            "slice_id": entering_slice,
            "at_count": at_count,
            "slice_max": slice_max,
            "error": (
                f"slice {entering_slice} has {at_count} ATs, exceeding the "
                f"carpaccio ceiling of {slice_max}"
            ),
            "instruction": (
                "re-slice into thinner end-to-end verticals each within the "
                f"ceiling of {slice_max}, or annotate the slice as @coupled / "
                "@walking-skeleton / @infrastructure with a recorded justification"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Assertion 5 -- the AT-review gate (ADR-029 D5)
# ---------------------------------------------------------------------------


def _load_signing_key(repo: Path) -> bytes | None:
    """Resolve the reviewer signing key: env first, file fallback."""
    env_value = os.environ.get(_SIGNING_KEY_ENV)
    if env_value:
        return env_value.encode("utf-8")
    key_file = repo / _SIGNING_KEY_FILE
    if key_file.is_file():
        return key_file.read_bytes().strip()
    return None


def canonical_at_review_json(record: dict[str, object]) -> bytes:
    """Serialize the seven signed fields of an ATReviewVerdict to canonical JSON.

    ADR-029 D5 B1: HMAC input is the UTF-8 bytes of ``json.dumps`` over EXACTLY
    the seven signed fields with sorted keys and no whitespace. ``event`` and
    ``findings_summary`` are NOT signed; ``hmac_sha256`` is the signature.
    """
    signed = {field: record[field] for field in _SIGNED_FIELDS}
    return json.dumps(signed, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _at_review_rejection(reason: str, slice_id: str) -> GateError:
    return GateError(
        45,
        {
            "event": "ATReviewGateRejected",
            "slice_id": slice_id,
            "reason": reason,
            "error": f"AT-review gate rejected slice {slice_id}: {reason}",
        },
    )


def _latest_verdict_record(
    ledger_path: Path, slice_id: str
) -> dict[str, object] | None:
    """Select the latest ATReviewVerdict record for the entering slice."""
    if not ledger_path.is_file():
        return None
    latest: dict[str, object] | None = None
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        if record.get("event") != "ATReviewVerdict":
            continue
        if record.get("slice_id") != slice_id:
            continue
        latest = record
    return latest


def check_at_review(
    repo: Path,
    feature_id: str,
    entering_slice: str,
    scenarios: list[Scenario],
) -> None:
    """Run assertion 5 (ADR-029 D5). Raises ``GateError`` exit 45 on failure.

    Fail-closed: an unresolvable signing key refuses the slice (reason
    ``key-absent``) -- the gate never passes blind. F-03 (atdd-pure-dogfooding-
    friction-2026-05-20.md): an entering slice that maps to ZERO ``@slice-NN``
    scenarios is rejected loud (reason ``no-scenarios-for-slice``), never
    cleared vacuously on an empty AT set.
    """
    key = _load_signing_key(repo)
    if key is None:
        raise _at_review_rejection("key-absent", entering_slice)

    record = _latest_verdict_record(_ledger_path(repo, feature_id), entering_slice)
    if record is None:
        raise _at_review_rejection("absent", entering_slice)

    if record.get("verdict") != "APPROVED":
        raise _at_review_rejection("not-approved", entering_slice)

    if not _hmac_verifies(record, key):
        raise _at_review_rejection("hmac-mismatch", entering_slice)

    slice_scenarios = _slice_scenarios(scenarios, entering_slice)
    expected_ids = {f"AT-{n}" for n in range(1, len(slice_scenarios) + 1)}
    record_ids = record.get("at_ids")
    if not isinstance(record_ids, list) or set(record_ids) != expected_ids:
        raise _at_review_rejection("stale-at-set", entering_slice)

    expected_hash = _at_content_hash(slice_scenarios)
    if record.get("at_content_hash") != expected_hash:
        raise _at_review_rejection("stale-at-content", entering_slice)


def _hmac_verifies(record: dict[str, object], key: bytes) -> bool:
    """Constant-time-compare the record HMAC over the seven signed fields."""
    signature = record.get("hmac_sha256")
    if not isinstance(signature, str):
        return False
    try:
        expected = hmac.new(
            key, canonical_at_review_json(record), hashlib.sha256
        ).hexdigest()
    except KeyError:
        return False
    return hmac.compare_digest(expected, signature)


def _at_content_hash(slice_scenarios: list[Scenario]) -> str:
    """SHA-256 over the sorted concatenation of normalized scenario bodies."""
    bodies = sorted(s.normalized_body for s in slice_scenarios)
    return hashlib.sha256("".join(bodies).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# CLI shell
# ---------------------------------------------------------------------------


def _emit(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="carpaccio_slice_gate",
        description=(
            "ATDD-pure DELIVER entry gate: carpaccio decomposition (ADR-028 "
            "D2-bis) + AT-review (ADR-029 D5)."
        ),
        epilog=(
            "Exit codes: 0 cleared | 1 missing slice plan | 2 malformed input "
            "| 44 oversized slice | 45 AT-review not approved."
        ),
    )
    parser.add_argument("--feature-id", required=True)
    parser.add_argument("--entering-slice", required=True)
    parser.add_argument("--repo-root", default=None)
    return parser.parse_args(sys.argv[1:] if argv is None else list(argv))


def main(argv: list[str] | None = None) -> int:
    """Carpaccio slice gate entry point.

    Pure-function contract (ADR-028 D2-bis): reads the feature-delta, the
    slice's ``.feature`` files, and the AT-completion ledger -- writes nothing.
    """
    args = _parse_args(argv)
    repo = _repo_root(args.repo_root)
    feature_id = args.feature_id
    entering_slice = args.entering_slice

    try:
        delta_path = _feature_delta_path(repo, feature_id)
        if not delta_path.is_file():
            raise GateError(
                1,
                {
                    "event": "SlicePlanSectionMissing",
                    "error": (
                        f"feature-delta not found: docs/feature/{feature_id}/"
                        "feature-delta.md"
                    ),
                },
            )
        plan = parse_slice_plan(delta_path.read_text(encoding="utf-8"))
        scenarios = parse_scenarios(_read_feature_files(repo, feature_id))
        slice_max = _config_slice_max(repo)
        coupled_event = check_carpaccio(plan, scenarios, entering_slice, slice_max)
        check_at_review(repo, feature_id, entering_slice, scenarios)
    except GateError as gate_error:
        _emit(gate_error.payload)
        return gate_error.exit_code

    payload: dict[str, object] = {
        "event": coupled_event["event"] if coupled_event else "SliceCleared",
        "slice_id": entering_slice,
        "feature_id": feature_id,
    }
    if coupled_event:
        payload.update(coupled_event)
    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
