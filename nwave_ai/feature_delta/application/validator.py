"""ValidationOrchestrator — application-layer use case for feature-delta validation."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from nwave_ai.feature_delta.domain.parser import MarkdownSectionParser
from nwave_ai.feature_delta.domain.rules import (
    e1_section_present,
    e2_columns_present,
    e3_non_empty_rows,
    e3b_cherry_pick,
    e3b_row_pairing,
    e4_substantive_impact,
    e5_protocol_surface,
)
from nwave_ai.feature_delta.domain.violations import (
    ValidationResult,
    ValidationViolation,
)


if TYPE_CHECKING:
    from nwave_ai.feature_delta.ports.filesystem import FileSystemReadPort
    from nwave_ai.feature_delta.ports.verbs import VerbListProviderPort


# Default maturity manifest path (relative to repo root / installed package).
# parents[0]=application/, parents[1]=feature_delta/, parents[2]=nwave_ai/, parents[3]=repo root
_DEFAULT_MANIFEST_PATH = (
    Path(__file__).parents[3] / "nWave" / "data" / "feature-delta-rule-maturity.json"
)


def _check_enforce_eligibility(manifest_path: Path | None) -> str | None:
    """
    Return an error message if enforce mode is ineligible, else None.

    Loads the maturity manifest and checks that every rule listed in
    enforce_eligibility.required_stable is actually marked 'stable'.
    Returns the error message string when ineligible (caller emits to stderr).
    """
    resolved = manifest_path if manifest_path is not None else _DEFAULT_MANIFEST_PATH
    if not resolved.exists():
        return f"maturity manifest not found: {resolved}"
    try:
        manifest = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"maturity manifest unreadable: {exc}"

    rules = manifest.get("rules", {})
    required = manifest.get("enforce_eligibility", {}).get("required_stable", [])
    pending = [r for r in required if rules.get(r, {}).get("status") != "stable"]
    if pending:
        return f"cannot enable --enforce: rules pending ({', '.join(pending)})"
    return None


def _emit_pass_marker(label: str, emit: bool) -> None:
    """Print a [PASS] marker to stdout when emit is True.

    Centralises the guard so call sites don't repeat the conditional.
    Suppressed in JSON mode because stdout is reserved for machine output.
    """
    if emit:
        print(f"[PASS] {label}", file=sys.stdout)


def _find_nested_fence(text: str, file_path: str) -> ValidationViolation | None:
    """Return a violation if a fenced block appears inside a table row."""
    lines = text.splitlines()
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("|") and "```" in stripped:
            return ValidationViolation(
                rule="E0-NESTED-FENCE",
                severity="error",
                file=file_path,
                line=lineno,
                offender=stripped[:80],
                remediation=(
                    "Remove the nested fenced code block from the "
                    "commitment cell. Use plain text in table cells."
                ),
            )
    return None


class ValidationOrchestrator:
    """Orchestrate feature-delta validation: read → parse → run rules → report."""

    def __init__(
        self,
        fs_reader: FileSystemReadPort | None = None,
        verb_loader: VerbListProviderPort | None = None,
        parser: MarkdownSectionParser | None = None,
        lang: str = "en",
    ) -> None:
        if fs_reader is None:
            from nwave_ai.feature_delta.adapters.filesystem import RealFileSystemReader

            fs_reader = RealFileSystemReader()
        if verb_loader is None:
            from nwave_ai.feature_delta.adapters.verbs import PlaintextVerbLoader

            verb_loader = PlaintextVerbLoader()
        self._fs = fs_reader
        self._verbs = verb_loader
        self._parser = parser or MarkdownSectionParser()
        self._lang = lang

    def validate(
        self,
        path: Path | str,
        mode: str = "warn-only",
        output_format: str = "human",
        maturity_manifest_path: Path | None = None,
        enabled_rules: frozenset[str] | None = None,
        fmt: str | None = None,
    ) -> ValidationResult:
        """
        Validate a feature-delta.md file.

        mode: "warn-only" (default) — emit [WARN] prefix, exit 0 on violations.
              "enforce"   — emit [FAIL] prefix, exit 1 on violations.
                           Caller is responsible for checking manifest eligibility
                           before invoking validate() in enforce mode.
        output_format: "human" (default) — human-readable text to stderr/stdout.
                       "json"  — machine-parseable JSON to stdout.
                                 Schema: {"schema_version": 1, "results": [{"check", "severity",
                                 "file", "line", "offender", "remediation"}, ...]}
        fmt: deprecated alias for output_format (kept for backwards compatibility).

        Returns a ValidationResult. Callers inspect .violations and .passed.
        Side-effects: writes diagnostics to stderr when violations found,
        and [PASS] markers to stdout when rules pass.
        """
        resolved_output_format = fmt if fmt is not None else output_format

        start = time.monotonic()
        target = Path(path)
        file_path = str(target)

        violation_prefix = "[WARN]" if mode == "warn-only" else "[FAIL]"
        emit_pass = resolved_output_format != "json"

        early_exit, text = self._read_and_check_preconditions(target, file_path, start)
        if early_exit is not None:
            return early_exit

        # E1 — section heading structure (operates on raw text)
        e1_violations = e1_section_present.check(text, file_path)
        if e1_violations:
            for v in e1_violations:
                msg = (
                    f"{violation_prefix} [{v.rule}] {target.name}:{v.line} — "
                    f"malformed wave heading '{v.offender}'."
                )
                if v.did_you_mean:
                    msg += f" Did you mean: '{v.did_you_mean}'?"
                print(msg, file=sys.stderr)
        elif emit_pass:
            _emit_pass_marker("E1", True)

        # E2 — column presence (operates on raw text)
        e2_violations = e2_columns_present.check(text, file_path)
        if e2_violations:
            for v in e2_violations:
                print(
                    f"{violation_prefix} [{v.rule}] {target.name}:{v.line} — "
                    f"missing column 'DDR'. {v.remediation}",
                    file=sys.stderr,
                )
        elif emit_pass:
            _emit_pass_marker("E2", True)

        model = self._parser.parse(text)

        # E3 — non-empty rows
        e3_violations = e3_non_empty_rows.check(model)
        if not e3_violations and emit_pass:
            _emit_pass_marker("E3", True)
        for v in e3_violations:
            print(
                f"{violation_prefix} [{v.rule}] {target.name}:{v.line} — "
                f"{v.offender}. {v.remediation}",
                file=sys.stderr,
            )

        # E3b — cherry-pick check
        e3b_violations = e3b_cherry_pick.check(model)
        if not e3b_violations and emit_pass:
            _emit_pass_marker("E3b", True)
        for v in e3b_violations:
            print(
                f"{violation_prefix} [{v.rule}] {target.name}:{v.line} — "
                f"commitment '{v.offender}' dropped without DDR ratification. "
                f"{v.remediation}",
                file=sys.stderr,
            )

        substantive_verbs = self._verbs.load_substantive_verbs(self._lang)

        # E4 — substantive impact heuristic: v1.1 when R2 enabled, else v1.0
        r2_violations: tuple[ValidationViolation, ...] = ()
        if enabled_rules and "R2" in enabled_rules:
            r2_violations = e4_substantive_impact.check_v1_1(model, substantive_verbs)
            if not r2_violations and emit_pass:
                _emit_pass_marker("E4 v1.1", True)
            for v in r2_violations:
                print(
                    f"{violation_prefix} [{v.rule}] {target.name}:{v.line} — "
                    f"impact '{v.offender}' too vague. {v.remediation}",
                    file=sys.stderr,
                )
            e4_violations: tuple[ValidationViolation, ...] = ()
        else:
            e4_violations = e4_substantive_impact.check_v1_0(model, substantive_verbs)
            if not e4_violations and emit_pass:
                _emit_pass_marker("E4", True)
            for v in e4_violations:
                print(
                    f"{violation_prefix} [{v.rule}] {target.name}:{v.line} — "
                    f"impact '{v.offender}' too vague. {v.remediation}",
                    file=sys.stderr,
                )

        patterns = self._verbs.load_protocol_verbs(self._lang)

        # E5 — protocol surface preservation
        e5_violations = e5_protocol_surface.check(model, patterns)
        if not e5_violations and emit_pass:
            _emit_pass_marker("E5", True)

        for v in e5_violations:
            print(
                f"{violation_prefix} [{v.rule}] {target.name}:{v.line} — "
                f"protocol surface '{v.offender}' missing in DESIGN. "
                f"{v.remediation}",
                file=sys.stderr,
            )

        # R1 — row-level bijection check (opt-in via --rule R1)

        r1_violations: tuple[ValidationViolation, ...] = ()
        if enabled_rules and "R1" in enabled_rules:
            r1_violations = e3b_row_pairing.check_row_pairing(model)
            if not r1_violations and emit_pass:
                _emit_pass_marker("E3b-row", True)
            for v in r1_violations:
                print(
                    f"{violation_prefix} [{v.rule}] {target.name}:{v.line} — "
                    f"upstream row '{v.offender}' has no downstream pairing. "
                    f"{v.remediation}",
                    file=sys.stderr,
                )

        all_violations = (
            e1_violations
            + e2_violations
            + e3_violations
            + e3b_violations
            + e4_violations
            + r2_violations
            + e5_violations
            + r1_violations
        )
        elapsed = int((time.monotonic() - start) * 1000)

        if resolved_output_format == "json":
            return self._emit_json_result(all_violations, elapsed)

        if not all_violations and emit_pass:
            print("[PASS] all checks", file=sys.stderr)

        # Opt-in rule violations (R1, R2) always block regardless of warn-only/enforce mode.
        if r1_violations or r2_violations:
            return ValidationResult(
                violations=tuple(all_violations),
                duration_ms=elapsed,
                exit_code_hint=1,
            )

        if mode == "warn-only" and all_violations:
            return ValidationResult(
                violations=tuple(all_violations),
                duration_ms=elapsed,
                exit_code_hint=0,
            )
        return ValidationResult(violations=tuple(all_violations), duration_ms=elapsed)

    def _read_and_check_preconditions(
        self,
        target: Path,
        file_path: str,
        start: float,
    ) -> tuple[ValidationResult | None, str]:
        """Read the file and check preconditions.

        Returns (None, text) on success, or (early_result, "") on failure.
        """
        try:
            text = self._fs.read_text(target)
        except PermissionError:
            elapsed = int((time.monotonic() - start) * 1000)
            print(f"ERROR {target}: permission denied", file=sys.stderr)
            return (
                ValidationResult(
                    violations=(
                        ValidationViolation(
                            rule="E0",
                            severity="error",
                            file=file_path,
                            line=0,
                            offender=file_path,
                            remediation="Check file permissions.",
                        ),
                    ),
                    duration_ms=elapsed,
                    exit_code_hint=65,
                ),
                "",
            )

        if not text.strip():
            elapsed = int((time.monotonic() - start) * 1000)
            print(
                f"ERROR {target.name}: file is empty. "
                "Run 'nwave-ai feature-delta init' to create a template.",
                file=sys.stderr,
            )
            return (
                ValidationResult(
                    violations=(
                        ValidationViolation(
                            rule="E0",
                            severity="error",
                            file=file_path,
                            line=0,
                            offender=file_path,
                            remediation="Run 'nwave-ai feature-delta init' to create a template.",
                        ),
                    ),
                    duration_ms=elapsed,
                    exit_code_hint=65,
                ),
                "",
            )

        nested_fence = _find_nested_fence(text, file_path)
        if nested_fence is not None:
            elapsed = int((time.monotonic() - start) * 1000)
            print(
                f"PARSE ERROR [{nested_fence.rule}] "
                f"{target.name}:{nested_fence.line} — "
                "nested fenced block detected in table row.",
                file=sys.stderr,
            )
            return (
                ValidationResult(
                    violations=(nested_fence,), duration_ms=elapsed, exit_code_hint=65
                ),
                "",
            )

        return None, text

    @staticmethod
    def _emit_json_result(
        all_violations: list[ValidationViolation],
        elapsed: int,
    ) -> ValidationResult:
        """Emit machine-parseable JSON to stdout and return the result.

        Schema: {"schema_version": 1, "results": [...]}
        JSON mode uses exit 1 when violations found — CI tools depend on exit codes,
        warn-only suppression does not apply to JSON output.
        """
        results = [
            {
                "check": v.rule,
                "severity": v.severity,
                "file": v.file,
                "line": v.line,
                "offender": v.offender,
                "remediation": v.remediation,
            }
            for v in all_violations
        ]
        print(json.dumps({"schema_version": 1, "results": results}))
        return ValidationResult(
            violations=tuple(all_violations),
            duration_ms=elapsed,
            exit_code_hint=1 if all_violations else None,
        )
