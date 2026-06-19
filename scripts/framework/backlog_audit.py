"""Backlog hygiene audit tool — acceptance tests as SSOT.

Reconciles `docs/backlog.md` claims of resolution against the existence and
GREEN status of acceptance tests. GitHub issue state is deliberately
excluded (procedural, not empirical — see ADR-AUDIT-004 in
`docs/analysis/backlog-audit-2026-05-03.md`).

The tool is a hypothesis generator, not an oracle. MISSING means "no test
found by heuristic", not "no test exists". Every flagged item requires
human review.

Usage:
    python scripts/framework/backlog_audit.py [--mode acceptance]

See `--help` for full options.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


# ─── Constants ──────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKLOG = REPO_ROOT / "docs" / "backlog.md"
DEFAULT_TESTS_ROOT = REPO_ROOT / "tests"

# Discovery search order (most-canonical first)
ACCEPTANCE_DISCOVERY_PATHS = (
    "tests/acceptance",
    "tests/des/acceptance",
    "tests/installer/acceptance",
    "tests/plugins/plugin-architecture/acceptance",
    "tests/bugs",
    "tests",  # fallback
)

# File-scan upper bound (Earned Trust: bounded I/O)
SCAN_LIMIT = 200

# Stopwords for keyword search (lowercase)
STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "in",
        "on",
        "for",
        "via",
        "with",
        "by",
        "of",
        "and",
        "or",
        "to",
        "is",
        "are",
        "was",
        "were",
        "be",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "as",
        "at",
        "from",
        "into",
        "out",
        "up",
        "down",
        "over",
        "under",
    }
)

# Process items heuristic — treat title containing these as UNVERIFIABLE
PROCESS_TITLE_KEYWORDS = frozenset(
    {
        "research",
        "investigate",
        "document",
        "documentation",
        "retro",
        "retrospective",
        "ssot phase",
        "priority:",
        "process",
        "workflow",
    }
)

# Escape hatch marker
NO_TEST_RE = re.compile(r"<!--\s*no-test:\s*(.+?)\s*-->", re.IGNORECASE)


# ─── Enums + Data Classes ───────────────────────────────────────────────────


class ClaimType(str, Enum):
    DONE = "DONE"
    PR = "PR"
    VERSION = "VERSION"
    TEST_REF = "TEST_REF"
    DOC = "DOC"
    UNKNOWN = "UNKNOWN"


class AuditStatus(str, Enum):
    GREEN = "GREEN"
    RED = "RED"
    MISSING = "MISSING"
    DOC_MITIGATED = "DOC_MITIGATED"
    UNVERIFIABLE = "UNVERIFIABLE"
    SKIPPED = "SKIPPED"


class TestOutcome(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_RUN = "NOT_RUN"
    NOT_COLLECTED = "NOT_COLLECTED"


@dataclass
class ResolutionClaim:
    claim_type: ClaimType
    evidence_text: str
    pr_number: int | None = None
    version: str | None = None
    test_ref: str | None = None
    doc_ref: str | None = None


@dataclass
class BacklogItem:
    title: str
    section: (
        str  # "Critical" | "High" | "Medium" | "Low" | "Future" | "Completed" | ...
    )
    raw_text: str
    resolution_claims: list[ResolutionClaim] = field(default_factory=list)
    issue_numbers: list[int] = field(default_factory=list)
    is_completed_section: bool = False
    no_test_reason: str | None = None  # from <!-- no-test: reason --> marker


@dataclass
class AuditResult:
    item: BacklogItem
    status: AuditStatus
    test_paths: list[Path] = field(default_factory=list)
    test_outcome: TestOutcome | None = None
    notes: str = ""


# ─── Parser ─────────────────────────────────────────────────────────────────


_SECTION_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$")
_ITEM_HEADER_RE = re.compile(r"^###\s+(.+?)\s*$")


def parse_backlog(text: str) -> list[BacklogItem]:
    """Parse a backlog Markdown document into BacklogItem records.

    State machine: tracks current `## Section` and accumulates lines per
    `### Item` until next item or section break. Items outside any section
    are dropped (e.g. document preamble before first ## heading).
    """
    items: list[BacklogItem] = []
    current_section = ""
    current_title: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_title is None:
            return
        raw = "\n".join(current_lines).strip()
        item = BacklogItem(
            title=current_title,
            section=current_section,
            raw_text=raw,
            is_completed_section=(current_section.lower() == "completed"),
        )
        item.resolution_claims = _extract_resolution_claims(raw)
        item.issue_numbers = _extract_issue_numbers(item.title + "\n" + raw)
        no_test_match = NO_TEST_RE.search(raw)
        if no_test_match:
            item.no_test_reason = no_test_match.group(1).strip()
        items.append(item)

    for line in text.splitlines():
        section_match = _SECTION_HEADER_RE.match(line)
        if section_match:
            flush()
            current_title = None
            current_lines = []
            current_section = section_match.group(1).strip()
            continue

        item_match = _ITEM_HEADER_RE.match(line)
        if item_match:
            flush()
            current_title = item_match.group(1).strip()
            current_lines = []
            continue

        if current_title is not None:
            current_lines.append(line)

    flush()
    return items


# ─── Resolution claim extraction ────────────────────────────────────────────


# Generic DONE marker — strict: only unambiguous closure verbs.
# "shipped" and "fixed" are AMBIGUOUS in partial-progress entries
# ("Q1+Q2 shipped" inside a still-open item) and trigger false positives.
# When a real ship event exists, it is captured by VERSION or PR claims.
_DONE_RE = re.compile(r"\bSTATUS\s*[:=]\s*(?:DONE|COMPLETED|CLOSED)\b", re.IGNORECASE)
_VERSION_RE = re.compile(
    r"(?:fixed|shipped|closed|landed|released)\s+in\s+(v?[\d]+\.[\d]+(?:\.[\d]+)?)",
    re.IGNORECASE,
)
_PR_RE = re.compile(r"(?:via\s+)?PR\s*#(\d+)", re.IGNORECASE)
_COMMIT_RE = re.compile(r"`([0-9a-f]{7,40})`")
_TEST_REF_RE = re.compile(r"`?(tests/(?:[^\s`]+/)?test_[A-Za-z0-9_]+\.py)`?")
_DOC_REF_RE = re.compile(
    r"\b(README|docs/[\w/.-]+\.md)\s+(warning|demotion|qualification|note|update)",
    re.IGNORECASE,
)
_README_DEMOTION_RE = re.compile(
    r"README\s+(?:demotion|qualification|warning|update)|"
    r"demoted?\s+via\s+README|"
    r"mitigated\s+via\s+(?:doc|readme|guide)",
    re.IGNORECASE,
)
_ISSUE_NUM_RE = re.compile(r"#(\d+)\b")


def _extract_resolution_claims(text: str) -> list[ResolutionClaim]:
    """Apply all claim regex patterns and return one entry per match."""
    claims: list[ResolutionClaim] = []

    for match in _VERSION_RE.finditer(text):
        claims.append(
            ResolutionClaim(
                claim_type=ClaimType.VERSION,
                evidence_text=match.group(0),
                version=match.group(1),
            )
        )

    for match in _PR_RE.finditer(text):
        claims.append(
            ResolutionClaim(
                claim_type=ClaimType.PR,
                evidence_text=match.group(0),
                pr_number=int(match.group(1)),
            )
        )

    for match in _TEST_REF_RE.finditer(text):
        claims.append(
            ResolutionClaim(
                claim_type=ClaimType.TEST_REF,
                evidence_text=match.group(0),
                test_ref=match.group(1),
            )
        )

    for match in _DOC_REF_RE.finditer(text):
        claims.append(
            ResolutionClaim(
                claim_type=ClaimType.DOC,
                evidence_text=match.group(0),
                doc_ref=match.group(1),
            )
        )

    if _README_DEMOTION_RE.search(text) and not any(
        c.claim_type == ClaimType.DOC for c in claims
    ):
        match = _README_DEMOTION_RE.search(text)
        if match is not None:
            claims.append(
                ResolutionClaim(
                    claim_type=ClaimType.DOC,
                    evidence_text=match.group(0),
                    doc_ref="README.md",
                )
            )

    # Generic DONE marker — only add if no more-specific claim present
    if _DONE_RE.search(text) and not claims:
        match = _DONE_RE.search(text)
        if match is not None:
            claims.append(
                ResolutionClaim(
                    claim_type=ClaimType.DONE,
                    evidence_text=match.group(0),
                )
            )

    return claims


def _extract_issue_numbers(text: str) -> list[int]:
    """Extract issue numbers from #N patterns (deduplicated, ordered)."""
    seen: set[int] = set()
    result: list[int] = []
    for match in _ISSUE_NUM_RE.finditer(text):
        n = int(match.group(1))
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result


# ─── Test discovery ─────────────────────────────────────────────────────────


def find_acceptance_tests(
    item: BacklogItem,
    repo_root: Path,
    tests_root: Path | None = None,
    scan_limit: int = SCAN_LIMIT,
) -> list[Path]:
    """Discover acceptance tests for a backlog item.

    Returns paths ordered by confidence (explicit > issue-grep > keyword-score).
    Empty list = no test found by heuristic.

    When ``tests_root`` is provided, discovery is scoped to that single root
    (overriding ``ACCEPTANCE_DISCOVERY_PATHS``). When ``None``, the default
    ACCEPTANCE_DISCOVERY_PATHS under ``repo_root`` are scanned.
    """
    discovered: list[Path] = []

    # Step 1: explicit test references
    for claim in item.resolution_claims:
        if claim.test_ref:
            ref_path = repo_root / claim.test_ref
            if ref_path.exists() and ref_path not in discovered:
                discovered.append(ref_path)

    # Build candidate file pool
    candidates = _candidate_test_files(repo_root, scan_limit, tests_root)

    # Step 2: issue number search
    if item.issue_numbers:
        for path in candidates:
            if path in discovered:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")[:50_000]
            except OSError:
                continue
            for n in item.issue_numbers:
                if f"#{n}" in content:
                    discovered.append(path)
                    break

    # Step 3: keyword search
    keywords = _extract_keywords(item.title)
    if keywords:
        scored: list[tuple[int, Path]] = []
        for path in candidates:
            if path in discovered:
                continue
            stem = path.stem.lower()
            stem_score = sum(1 for kw in keywords if kw in stem)
            try:
                head = path.read_text(encoding="utf-8", errors="ignore")[:5_000].lower()
            except OSError:
                head = ""
            head_score = sum(1 for kw in keywords if kw in head)
            score = stem_score * 2 + head_score  # filename matches weighted higher
            if score >= 2:
                scored.append((score, path))
        scored.sort(key=lambda x: x[0], reverse=True)
        for _, path in scored:
            discovered.append(path)

    return discovered


def _candidate_test_files(
    repo_root: Path,
    scan_limit: int,
    tests_root: Path | None = None,
) -> list[Path]:
    """Collect Python test files under canonical acceptance roots.

    When ``tests_root`` is provided, scan only that directory (used by callers
    that need isolation, e.g. unit tests of this module). Otherwise iterate
    ACCEPTANCE_DISCOVERY_PATHS under repo_root.
    """
    seen: set[Path] = set()
    result: list[Path] = []
    if tests_root is not None:
        roots: list[Path] = [tests_root]
    else:
        roots = [repo_root / relative for relative in ACCEPTANCE_DISCOVERY_PATHS]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("test_*.py"):
            if path in seen:
                continue
            seen.add(path)
            result.append(path)
            if len(result) >= scan_limit:
                return result
    return result


def _extract_keywords(title: str) -> list[str]:
    """Extract meaningful keyword tokens from an item title."""
    cleaned = re.sub(r"[^\w\s-]", " ", title.lower())
    tokens = re.split(r"[\s-]+", cleaned)
    return [t for t in tokens if len(t) >= 4 and t not in STOPWORDS]


# ─── Audit orchestration ────────────────────────────────────────────────────


def classify_item(
    item: BacklogItem,
    test_paths: list[Path],
    repo_root: Path,
) -> AuditResult:
    """Compute the audit status for an item before any test execution."""
    # SKIPPED: items already in Completed section
    if item.is_completed_section:
        return AuditResult(
            item=item,
            status=AuditStatus.SKIPPED,
            test_paths=test_paths,
            notes="Item lives in Completed section",
        )

    # Explicit no-test escape hatch
    if item.no_test_reason:
        return AuditResult(
            item=item,
            status=AuditStatus.UNVERIFIABLE,
            test_paths=test_paths,
            notes=f"no-test marker: {item.no_test_reason}",
        )

    # Process-item heuristic
    title_lower = item.title.lower()
    if any(kw in title_lower for kw in PROCESS_TITLE_KEYWORDS):
        return AuditResult(
            item=item,
            status=AuditStatus.UNVERIFIABLE,
            test_paths=test_paths,
            notes="Title matches process-item heuristic",
        )

    # No resolution claim → not asserting fixed
    if not item.resolution_claims:
        return AuditResult(
            item=item,
            status=AuditStatus.UNVERIFIABLE,
            test_paths=test_paths,
            notes="No resolution claim found in item text",
        )

    # DOC_MITIGATED branch
    doc_claims = [c for c in item.resolution_claims if c.claim_type == ClaimType.DOC]
    if doc_claims and not test_paths:
        for claim in doc_claims:
            if claim.doc_ref:
                ref_path = repo_root / claim.doc_ref
                if ref_path.exists():
                    return AuditResult(
                        item=item,
                        status=AuditStatus.DOC_MITIGATED,
                        test_paths=[],
                        notes=f"Doc reference verified: {claim.doc_ref}",
                    )
        return AuditResult(
            item=item,
            status=AuditStatus.MISSING,
            test_paths=[],
            notes="DOC claim made but referenced file does not exist",
        )

    # No tests found → MISSING
    if not test_paths:
        return AuditResult(
            item=item,
            status=AuditStatus.MISSING,
            test_paths=[],
            notes="Resolution claim present but no acceptance test found by heuristic",
        )

    # Tests found, status determined by execution (caller decides)
    return AuditResult(
        item=item,
        status=AuditStatus.GREEN,  # provisional; runner may downgrade to RED
        test_paths=test_paths,
        notes=f"Found {len(test_paths)} candidate test file(s)",
    )


# ─── Runner ─────────────────────────────────────────────────────────────────


def run_pytest(
    test_paths: list[Path],
    mode: str,
    repo_root: Path,
    timeout: int = 300,
) -> TestOutcome:
    """Run pytest on the given test paths and return outcome.

    mode:
      - "collect-only": pytest --collect-only (verifies importability only)
      - "acceptance":   pytest -x -q (run-and-fail-fast)
      - "no-run":       skip subprocess entirely
    """
    if not test_paths or mode == "no-run":
        return TestOutcome.NOT_RUN

    pytest_cmd = ["python", "-m", "pytest", "-q", "--tb=no"]
    if mode == "collect-only":
        pytest_cmd.append("--collect-only")
    elif mode == "acceptance":
        pytest_cmd.append("-x")

    pytest_cmd.extend(str(p) for p in test_paths)

    try:
        result = subprocess.run(
            pytest_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=repo_root,
        )
    except subprocess.TimeoutExpired:
        return TestOutcome.NOT_RUN
    except (FileNotFoundError, subprocess.SubprocessError):
        return TestOutcome.NOT_RUN

    if mode == "collect-only":
        return (
            TestOutcome.PASSED if result.returncode == 0 else TestOutcome.NOT_COLLECTED
        )
    return TestOutcome.PASSED if result.returncode == 0 else TestOutcome.FAILED


# ─── Report ─────────────────────────────────────────────────────────────────


def render_markdown_report(results: list[AuditResult], mode: str) -> str:
    """Render audit results as markdown."""
    counts: dict[AuditStatus, int] = dict.fromkeys(AuditStatus, 0)
    for r in results:
        counts[r.status] += 1

    total_audited = sum(counts[s] for s in AuditStatus if s != AuditStatus.SKIPPED)
    actionable = counts[AuditStatus.RED] + counts[AuditStatus.MISSING]

    lines = [
        "# Backlog Audit Report",
        "",
        f"**Mode**: {mode}",
        f"**Items audited**: {total_audited}",
        f"**Skipped (Completed section)**: {counts[AuditStatus.SKIPPED]}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| GREEN | {counts[AuditStatus.GREEN]} |",
        f"| RED | {counts[AuditStatus.RED]} |",
        f"| MISSING | {counts[AuditStatus.MISSING]} |",
        f"| DOC_MITIGATED | {counts[AuditStatus.DOC_MITIGATED]} |",
        f"| UNVERIFIABLE | {counts[AuditStatus.UNVERIFIABLE]} |",
        "",
        f"**Action required**: {actionable} items (RED={counts[AuditStatus.RED]} MISSING={counts[AuditStatus.MISSING]})",
        "",
    ]

    actionable_items = [
        r for r in results if r.status in (AuditStatus.RED, AuditStatus.MISSING)
    ]
    if actionable_items:
        lines.append("## Items Requiring Action\n")
        for r in actionable_items:
            lines.extend(_render_item_block(r))

    clean_items = [
        r for r in results if r.status in (AuditStatus.GREEN, AuditStatus.DOC_MITIGATED)
    ]
    if clean_items:
        lines.append("\n## Items Verified Clean\n")
        for r in clean_items:
            lines.extend(_render_item_block(r))

    unverifiable_items = [r for r in results if r.status == AuditStatus.UNVERIFIABLE]
    if unverifiable_items:
        lines.append("\n## Human review required (no test expected)\n")
        for r in unverifiable_items:
            lines.extend(_render_item_block(r))

    lines.append("\n---\n")
    lines.append(
        "*Honest limitations*: parsing is heuristic; MISSING means 'no test found",
    )
    lines.append(
        "by heuristic' not 'no test exists'. GREEN means a matching-keyword test passes,"
    )
    lines.append(
        "not that the item is fully resolved. Every flag requires human review."
    )
    return "\n".join(lines) + "\n"


def _render_item_block(result: AuditResult) -> list[str]:
    item = result.item
    claims_summary = (
        ", ".join(c.evidence_text for c in item.resolution_claims[:5]) or "none"
    )
    test_summary = (
        ", ".join(str(p.relative_to(REPO_ROOT)) for p in result.test_paths[:5])
        if result.test_paths
        else "none"
    )
    return [
        f"### [{result.status.value}] {item.title} ({item.section})",
        f"- **Claims**: {claims_summary}",
        f"- **Tests**: {test_summary}",
        f"- **Outcome**: {result.test_outcome.value if result.test_outcome else 'n/a'}",
        f"- **Notes**: {result.notes}",
        "",
    ]


def render_json_report(results: list[AuditResult]) -> str:
    """Render audit results as JSON."""
    payload = {
        "results": [
            {
                "title": r.item.title,
                "section": r.item.section,
                "status": r.status.value,
                "test_paths": [str(p.relative_to(REPO_ROOT)) for p in r.test_paths],
                "test_outcome": r.test_outcome.value if r.test_outcome else None,
                "claims": [c.evidence_text for c in r.item.resolution_claims],
                "issue_numbers": r.item.issue_numbers,
                "notes": r.notes,
            }
            for r in results
        ]
    }
    return json.dumps(payload, indent=2) + "\n"


# ─── CLI ────────────────────────────────────────────────────────────────────


def audit(
    backlog_path: Path,
    tests_root: Path,
    repo_root: Path,
    mode: str,
    sections_filter: list[str] | None,
    check_completed: bool,
) -> list[AuditResult]:
    """Run the full audit and return results."""
    text = backlog_path.read_text(encoding="utf-8")
    items = parse_backlog(text)

    if sections_filter:
        sections_lower = {s.lower() for s in sections_filter}
        items = [
            i
            for i in items
            if i.section.lower() in sections_lower
            or (check_completed and i.is_completed_section)
        ]

    results: list[AuditResult] = []
    for item in items:
        test_paths = find_acceptance_tests(item, repo_root, tests_root)
        result = classify_item(item, test_paths, repo_root)

        # Run tests for items provisionally GREEN
        if result.status == AuditStatus.GREEN and mode != "no-run":
            outcome = run_pytest(test_paths, mode, repo_root)
            result.test_outcome = outcome
            if outcome == TestOutcome.FAILED:
                result.status = AuditStatus.RED
                result.notes = f"Test execution failed: {result.notes}"
            elif outcome == TestOutcome.NOT_COLLECTED:
                result.status = AuditStatus.MISSING
                result.notes = f"Test files not collectable: {result.notes}"

        results.append(result)

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit docs/backlog.md against acceptance test SSOT. "
            "Heuristic parser — every flag requires human review."
        ),
    )
    parser.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    parser.add_argument("--tests-root", type=Path, default=DEFAULT_TESTS_ROOT)
    parser.add_argument(
        "--mode",
        choices=("collect-only", "acceptance", "no-run"),
        default="acceptance",
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--sections",
        type=lambda s: [x.strip() for x in s.split(",")],
        default=["Critical", "High"],
        help="Comma-separated sections to audit (default: Critical,High)",
    )
    parser.add_argument("--check-completed", action="store_true")

    args = parser.parse_args(argv)

    if not args.backlog.exists():
        print(f"ERROR: Backlog not found at {args.backlog}", file=sys.stderr)
        return 2

    try:
        results = audit(
            backlog_path=args.backlog,
            tests_root=args.tests_root,
            repo_root=REPO_ROOT,
            mode=args.mode,
            sections_filter=args.sections,
            check_completed=args.check_completed,
        )
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        report = render_json_report(results)
    else:
        report = render_markdown_report(results, args.mode)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    has_actionable = any(
        r.status in (AuditStatus.RED, AuditStatus.MISSING) for r in results
    )
    return 1 if has_actionable else 0


if __name__ == "__main__":
    sys.exit(main())
