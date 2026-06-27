"""
Feature-delta CLI subapp.

Per ADR-05, this module registers `validate-feature-delta`,
`extract-gherkin`, and `migrate-feature` subcommands under the parent
`nwave-ai` typer app.
"""

from __future__ import annotations

import sys
from pathlib import Path


def validate_feature_delta_command(
    path: str,
    mode: str = "warn-only",
    fmt: str = "human",
    maturity_manifest_path: Path | None = None,
    enabled_rules: frozenset[str] | None = None,
    lang: str = "en",
) -> int:
    """
    Validate a feature-delta.md file for cross-wave drift.

    mode: "warn-only" (default at v1.0) — report violations with [WARN] prefix,
          exit 0. Switch to --enforce once the maturity manifest marks all
          required rules stable (criterion: 30 days post-ship OR >=3 features
          migrated voluntarily — see CHANGELOG).
          "enforce" — report violations with [FAIL] prefix, exit 1.
          Refused (EX_CONFIG=78) when the maturity manifest marks any required
          rule as pending.
    fmt:  "human" (default) — human-readable text to stderr/stdout.
          "json"  — machine-parseable JSON to stdout (schema_version 1).

    Exit codes:
      0  — no violations (or warn-only mode with violations)
      1  — one or more violations found (enforce mode only)
      2  — usage error (file not found — did you typo the path?)
      65 — input error (empty file, permission denied, parse error)
      70 — startup refused (bad config)
      78 — misconfiguration (enforce mode + pending rules in maturity manifest)
    """
    from nwave_ai.feature_delta.adapters.schema import JsonSchemaFileLoader
    from nwave_ai.feature_delta.adapters.verbs import PlaintextVerbLoader, ReDoSError
    from nwave_ai.feature_delta.application.validator import (
        ValidationOrchestrator,
        _check_enforce_eligibility,
    )

    # Startup health-check: probe() exits 70 on schema corruption (DD-A7).
    JsonSchemaFileLoader().probe()

    # Startup health-check: ReDoS guard on per-repo override (US-13 AC-4/AC-6).
    # Use CWD so the sandbox-relative .nwave/protocol-verbs.txt is found.
    try:
        PlaintextVerbLoader(cwd_root=Path.cwd()).probe()
    except ReDoSError as exc:
        print(f"health.startup.refused: {exc}", file=sys.stderr)
        return 70

    # DD-A2 maturity gate: refuse --enforce when any required rule is pending.
    if mode == "enforce":
        error_msg = _check_enforce_eligibility(maturity_manifest_path)
        if error_msg is not None:
            print(error_msg, file=sys.stderr)
            return 78

    target = Path(path)
    if not target.exists():
        # Exit 2: usage error — path doesn't exist. Suggest closest match.
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        _suggest_closest_path(path)
        return 2

    orchestrator = ValidationOrchestrator(lang=lang)
    result = orchestrator.validate(
        target,
        mode=mode,
        output_format=fmt,
        maturity_manifest_path=maturity_manifest_path,
        enabled_rules=enabled_rules,
    )

    if result.exit_code_hint is not None:
        return result.exit_code_hint

    if result.passed:
        return 0
    return 1


def _suggest_closest_path(path: str) -> None:
    """Emit a did-you-mean hint to stderr when the path doesn't exist.

    Walks the parent directory (if it exists) and finds the closest
    filename match by edit distance. Emits nothing if no plausible
    candidate exists. Pure side-effect function.
    """
    import difflib

    target = Path(path)
    parent = target.parent
    if not parent.is_dir():
        return

    candidates = [p.name for p in parent.iterdir() if p.is_file()]
    if not candidates:
        return

    close = difflib.get_close_matches(target.name, candidates, n=1, cutoff=0.5)
    if close:
        suggestion = parent / close[0]
        print(f"Did you mean: {suggestion}?", file=sys.stderr)


def extract_gherkin_command(path: str | None = None) -> int:
    """Extract embedded Gherkin blocks from a feature-delta.md file.

    Reads the file at PATH, extracts all fenced ```gherkin blocks in
    document order, and emits to stdout beginning with "Feature: <id>".

    Exit codes:
      0  — extraction successful; output written to stdout
      1  — no gherkin blocks found or input error
      65 — file not found or unreadable
    """
    from nwave_ai.feature_delta.application.extractor import (
        ExtractionError,
        GherkinExtractor,
    )

    if not path:
        print("Usage: extract-gherkin <path>", file=sys.stderr)
        return 65

    target = Path(path)
    if not target.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 65

    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
        return 65

    try:
        output = GherkinExtractor().extract(text, path=str(target))
    except ExtractionError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(output, end="")
    return 0


def init_scaffold_command(
    feature_name: str,
    output_dir: Path | None = None,
) -> int:
    """Create a scaffold feature-delta.md with three pre-populated wave sections.

    Creates docs/feature/<feature_name>/feature-delta.md relative to output_dir
    (defaults to CWD). The scaffold passes E1+E2 validator immediately.

    Wave sections created: DISCUSS, DESIGN, DISTILL — each with a
    [REF] Inherited commitments table using the 4-column schema.

    Exit codes:
      0  — scaffold created successfully
      1  — output_dir not a directory or write error
    """
    base = output_dir if output_dir is not None else Path.cwd()
    target_dir = base / "docs" / "feature" / feature_name
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"ERROR: cannot create directory {target_dir}: {exc}", file=sys.stderr)
        return 1

    delta_path = target_dir / "feature-delta.md"

    _EMPTY_TABLE = (
        "| Origin | Commitment | DDR | Impact |\n"
        "|--------|------------|-----|--------|\n"
    )
    _WAVE_SECTION = (
        "## Wave: {wave}\n\n### [REF] Inherited commitments\n\n" + _EMPTY_TABLE
    )

    content = f"# {feature_name}\n\n"
    for wave in ("DISCUSS", "DESIGN", "DISTILL"):
        content += _WAVE_SECTION.format(wave=wave) + "\n"

    try:
        delta_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write {delta_path}: {exc}", file=sys.stderr)
        return 1

    print(f"Created: {delta_path}", file=sys.stderr)
    return 0


def migrate_feature_command(feature_dir: str | None = None) -> int:
    """Migrate .feature files in feature_dir to embedded gherkin blocks.

    Reads each .feature file, embeds its content as a fenced gherkin block
    in feature-delta.md, performs a byte-identical round-trip check, and
    renames originals to .feature.pre-migration on success.

    Re-running on an already-migrated directory (detected by presence of
    .feature.pre-migration files) is a no-op (exit 0, stderr notice).

    Exit codes:
      0  — migration succeeded or directory already migrated
      1  — round-trip check failed or input error
    """
    from nwave_ai.feature_delta.adapters.migration import MigrationApplier

    if not feature_dir:
        print("Usage: migrate-feature <directory>", file=sys.stderr)
        return 1

    # Normalize the legacy DDD decision column/refs to DDR before migrating
    # gherkin (issue #50 deprecation window). Independent of the gherkin
    # round-trip; only rewrites the feature-delta.md when it actually changes.
    _normalize_delta_columns(feature_dir)

    MigrationApplier().probe()
    return MigrationApplier().apply(feature_dir)


def _normalize_delta_columns(feature_dir: str) -> None:
    """Rewrite a legacy DDD feature-delta.md to the canonical DDR form.

    No-op when the directory or feature-delta.md is absent, or when the file is
    already in DDR form. Pure side-effect helper for migrate-feature.
    """
    from nwave_ai.feature_delta.domain.normalize import normalize_decision_refs

    base = Path(feature_dir)
    if not base.is_absolute():
        base = Path.cwd() / base
    delta_path = base / "feature-delta.md"
    if not delta_path.is_file():
        return

    original = delta_path.read_text(encoding="utf-8")
    normalized = normalize_decision_refs(original)
    if normalized != original:
        delta_path.write_text(normalized, encoding="utf-8")
        print(f"normalized DDD→DDR decision column in {delta_path}", file=sys.stderr)


_HELP_TEXT = """\
nwave-ai feature-delta subcommands

USAGE
  nwave-ai validate-feature-delta <path> [--warn-only | --enforce]
  nwave-ai extract-gherkin
  nwave-ai migrate-feature

SUBCOMMANDS
  validate-feature-delta <path>
      Validate a feature-delta.md file for cross-wave drift.

      --warn-only  (default at v1.0)
          Report violations with [WARN] prefix and exit 0.
          Use this mode while rules are still maturing.
          Switch criterion: 30 days post-ship OR >=3 features migrated
          voluntarily (see CHANGELOG).

      --enforce
          Report violations with [FAIL] prefix and exit 1.
          Refused (exit 78) when the rule maturity manifest marks any
          required rule as pending (DD-A2 gate).

EXIT CODES
  0   no violations (or warn-only mode — violations present but non-blocking)
  1   violations found (enforce mode only)
  65  input error (file not found, empty, permission denied, parse error)
  70  startup refused (bad schema config)
  78  misconfiguration (--enforce with pending rules in maturity manifest)
"""


def main(argv: list[str] | None = None) -> int:
    """Dispatch feature-delta subcommands from argv."""
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(_HELP_TEXT)
        return 0 if args and args[0] in ("-h", "--help") else 1

    subcommand = args[0]
    rest = args[1:]

    if subcommand == "validate-feature-delta":
        if not rest:
            print(
                "Usage: validate-feature-delta <path> [--warn-only | --enforce]",
                file=sys.stderr,
            )
            return 2

        # Parse positional path and optional mode/format/manifest/rule/lang flags.
        mode = "warn-only"
        fmt = "human"
        lang = "en"
        maturity_manifest_path: Path | None = None
        extra_rules: set[str] = set()
        cleaned: list[str] = []
        remaining = list(rest)
        i = 0
        while i < len(remaining):
            token = remaining[i]
            if token == "--warn-only":
                mode = "warn-only"
            elif token == "--enforce":
                mode = "enforce"
            elif token in ("--format=json", "--format json"):
                fmt = "json"
            elif token == "--format" and i + 1 < len(remaining):
                fmt = remaining[i + 1]
                i += 1
            elif token.startswith("--format="):
                fmt = token[len("--format=") :]
            elif token == "--maturity-manifest" and i + 1 < len(remaining):
                maturity_manifest_path = Path(remaining[i + 1])
                i += 1
            elif token == "--rule" and i + 1 < len(remaining):
                extra_rules.add(remaining[i + 1].upper())
                i += 1
            elif token.startswith("--rule="):
                extra_rules.add(token[len("--rule=") :].upper())
            elif token == "--lang" and i + 1 < len(remaining):
                lang = remaining[i + 1]
                i += 1
            elif token.startswith("--lang="):
                lang = token[len("--lang=") :]
            else:
                cleaned.append(token)
            i += 1

        if not cleaned:
            print(
                "Usage: validate-feature-delta <path> [--warn-only | --enforce] [--format=json]",
                file=sys.stderr,
            )
            return 2
        path_arg = cleaned[0]
        enabled_rules = frozenset(extra_rules) if extra_rules else None
        return validate_feature_delta_command(
            path_arg,
            mode=mode,
            fmt=fmt,
            maturity_manifest_path=maturity_manifest_path,
            enabled_rules=enabled_rules,
            lang=lang,
        )

    if subcommand == "extract-gherkin":
        return extract_gherkin_command(*rest)

    if subcommand == "migrate-feature":
        return migrate_feature_command(*rest)

    if subcommand == "init-scaffold":
        # Usage: init-scaffold --feature <name>
        feature_name: str | None = None
        i = 0
        while i < len(rest):
            if rest[i] == "--feature" and i + 1 < len(rest):
                feature_name = rest[i + 1]
                i += 2
            elif rest[i].startswith("--feature="):
                feature_name = rest[i][len("--feature=") :]
                i += 1
            else:
                i += 1
        if not feature_name:
            print("Usage: init-scaffold --feature <name>", file=sys.stderr)
            return 1
        return init_scaffold_command(feature_name)

    print(f"Unknown feature-delta subcommand: {subcommand}", file=sys.stderr)
    return 1
