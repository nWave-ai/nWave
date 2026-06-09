"""Unit tests for scripts/framework/backlog_audit.py.

Per the design's Earned Trust self-application requirement (section 8),
this validates parser, claim extraction, test discovery, and CLI exit
codes against fixture inputs. No subprocess pytest invocation; runner
behavior is exercised via classify_item only.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# Load the script as a module (not under a package — it's a CLI utility)
_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "framework" / "backlog_audit.py"
)
_spec = importlib.util.spec_from_file_location("backlog_audit", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
sys.modules["backlog_audit"] = _module
_spec.loader.exec_module(_module)

ClaimType = _module.ClaimType
AuditStatus = _module.AuditStatus
parse_backlog = _module.parse_backlog
_extract_resolution_claims = _module._extract_resolution_claims
_extract_issue_numbers = _module._extract_issue_numbers
_extract_keywords = _module._extract_keywords
find_acceptance_tests = _module.find_acceptance_tests
classify_item = _module.classify_item
BacklogItem = _module.BacklogItem
ResolutionClaim = _module.ResolutionClaim


# ─── Parser tests ──────────────────────────────────────────────────────────


class TestParser:
    """parse_backlog state machine extracts items keyed by section heading."""

    def test_extracts_one_item_per_h3_under_section(self):
        text = (
            "## Critical\n"
            "\n"
            "### Item One\n"
            "- Body line 1\n"
            "- Body line 2\n"
            "\n"
            "### Item Two\n"
            "- Body of two\n"
        )
        items = parse_backlog(text)
        assert len(items) == 2
        assert items[0].title == "Item One"
        assert items[0].section == "Critical"
        assert items[1].title == "Item Two"

    def test_section_change_resets_assignment(self):
        text = "## High\n### Item A\n- a\n## Medium\n### Item B\n- b\n"
        items = parse_backlog(text)
        assert items[0].section == "High"
        assert items[1].section == "Medium"

    def test_completed_section_marks_flag(self):
        text = "## Completed\n### Done Item\n- done\n"
        items = parse_backlog(text)
        assert items[0].is_completed_section is True

    def test_no_test_marker_extracted(self):
        text = (
            "## High\n"
            "### Process Item\n"
            "- description\n"
            "- <!-- no-test: this is a doc-only retro -->\n"
        )
        items = parse_backlog(text)
        assert items[0].no_test_reason == "this is a doc-only retro"

    def test_preamble_before_first_section_dropped(self):
        text = "# Backlog\nSome preamble text\n## Critical\n### Real Item\n- body\n"
        items = parse_backlog(text)
        assert len(items) == 1
        assert items[0].title == "Real Item"


# ─── Resolution claim extraction tests ─────────────────────────────────────


class TestClaimExtraction:
    """_extract_resolution_claims maps regex patterns to ClaimType records."""

    def test_pr_reference(self):
        claims = _extract_resolution_claims("Fixed via PR #14 and PR #17")
        prs = [c for c in claims if c.claim_type == ClaimType.PR]
        assert {c.pr_number for c in prs} == {14, 17}

    def test_version_reference(self):
        claims = _extract_resolution_claims("Closed in v3.4.0 with manifest tracking")
        versions = [c for c in claims if c.claim_type == ClaimType.VERSION]
        assert len(versions) == 1
        assert versions[0].version == "v3.4.0"

    def test_test_path_reference(self):
        claims = _extract_resolution_claims(
            "Validated in `tests/test_guard_fixtures.py` (10/10)"
        )
        refs = [c for c in claims if c.claim_type == ClaimType.TEST_REF]
        assert len(refs) == 1
        assert refs[0].test_ref == "tests/test_guard_fixtures.py"

    def test_doc_mitigation_explicit(self):
        claims = _extract_resolution_claims("Mitigated via README demotion 2026-04-16")
        docs = [c for c in claims if c.claim_type == ClaimType.DOC]
        assert len(docs) == 1

    def test_done_marker_only_when_no_other_claim(self):
        claims = _extract_resolution_claims("Status: DONE")
        done = [c for c in claims if c.claim_type == ClaimType.DONE]
        assert len(done) == 1

    def test_done_marker_suppressed_when_pr_present(self):
        claims = _extract_resolution_claims("Done — fixed via PR #14")
        # Specific PR claim wins over generic DONE
        assert any(c.claim_type == ClaimType.PR for c in claims)
        assert not any(c.claim_type == ClaimType.DONE for c in claims)


# ─── Issue + keyword tests ──────────────────────────────────────────────────


class TestIssueAndKeywords:
    def test_issue_numbers_dedup_in_order(self):
        nums = _extract_issue_numbers("Closes #29, #33, references #29 again")
        assert nums == [29, 33]

    def test_keyword_filter_drops_stopwords_and_short(self):
        kws = _extract_keywords("User-owned skill files deleted on reinstall")
        assert "user" in kws  # 4 chars: kept
        assert "owned" in kws
        assert "skill" in kws
        assert "files" in kws
        assert "deleted" in kws
        assert "reinstall" in kws
        assert "on" not in kws  # stopword + < 4 chars

    def test_keyword_handles_punctuation(self):
        kws = _extract_keywords("nWave doesn't update from plugin to v3.3.0")
        assert "nwave" in kws
        assert "update" in kws
        assert "plugin" in kws


# ─── Test discovery tests ──────────────────────────────────────────────────


class TestTestDiscovery:
    def test_explicit_test_ref_resolved_first(self, tmp_path):
        repo = tmp_path
        (repo / "tests").mkdir()
        target = repo / "tests" / "test_explicit.py"
        target.write_text("# explicit reference target\n")

        item = BacklogItem(
            title="Some item",
            section="High",
            raw_text="ref `tests/test_explicit.py`",
            resolution_claims=[
                ResolutionClaim(
                    claim_type=ClaimType.TEST_REF,
                    evidence_text="tests/test_explicit.py",
                    test_ref="tests/test_explicit.py",
                )
            ],
        )
        paths = find_acceptance_tests(item, repo)
        assert paths == [target]

    def test_issue_grep_finds_test_with_issue_ref(self, tmp_path):
        repo = tmp_path
        (repo / "tests" / "acceptance").mkdir(parents=True)
        target = repo / "tests" / "acceptance" / "test_skill_wipe.py"
        target.write_text(
            "# Regression for issue #29 user skill wipe\n"
            "def test_skill_preserved_on_reinstall(): pass\n"
        )

        item = BacklogItem(
            title="User skill deleted on reinstall",
            section="High",
            raw_text="See #29",
            issue_numbers=[29],
        )
        paths = find_acceptance_tests(item, repo)
        assert target in paths

    def test_keyword_search_finds_test_by_filename_score(self, tmp_path):
        repo = tmp_path
        (repo / "tests" / "acceptance").mkdir(parents=True)
        target = repo / "tests" / "acceptance" / "test_uninstall_residuals.py"
        target.write_text(
            '"""Regression for uninstall residual artifacts."""\n'
            "def test_no_residual_skills(): pass\n"
        )

        item = BacklogItem(
            title="uninstall residual artifacts cleanup",
            section="High",
            raw_text="body",
        )
        paths = find_acceptance_tests(item, repo)
        assert target in paths


# ─── classify_item tests ────────────────────────────────────────────────────


class TestClassifier:
    def test_skipped_for_completed_section(self, tmp_path):
        item = BacklogItem(
            title="X", section="Completed", raw_text="", is_completed_section=True
        )
        result = classify_item(item, [], tmp_path)
        assert result.status == AuditStatus.SKIPPED

    def test_unverifiable_for_no_test_marker(self, tmp_path):
        item = BacklogItem(
            title="Process Y",
            section="High",
            raw_text="<!-- no-test: process item -->",
            no_test_reason="process item",
            resolution_claims=[
                ResolutionClaim(claim_type=ClaimType.DONE, evidence_text="DONE")
            ],
        )
        result = classify_item(item, [], tmp_path)
        assert result.status == AuditStatus.UNVERIFIABLE

    def test_unverifiable_for_research_title(self, tmp_path):
        item = BacklogItem(
            title="Research framework — investigate X",
            section="High",
            raw_text="...",
            resolution_claims=[
                ResolutionClaim(claim_type=ClaimType.DONE, evidence_text="completed")
            ],
        )
        result = classify_item(item, [], tmp_path)
        assert result.status == AuditStatus.UNVERIFIABLE

    def test_doc_mitigated_when_doc_claim_and_file_exists(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Readme\n")
        item = BacklogItem(
            title="Plugin compat",
            section="Critical",
            raw_text="Mitigated via README demotion",
            resolution_claims=[
                ResolutionClaim(
                    claim_type=ClaimType.DOC,
                    evidence_text="README demotion",
                    doc_ref="README.md",
                )
            ],
        )
        result = classify_item(item, [], tmp_path)
        assert result.status == AuditStatus.DOC_MITIGATED

    def test_missing_when_doc_claim_but_file_absent(self, tmp_path):
        item = BacklogItem(
            title="Plugin compat",
            section="Critical",
            raw_text="Mitigated via README demotion",
            resolution_claims=[
                ResolutionClaim(
                    claim_type=ClaimType.DOC,
                    evidence_text="README demotion",
                    doc_ref="MISSING.md",
                )
            ],
        )
        result = classify_item(item, [], tmp_path)
        assert result.status == AuditStatus.MISSING

    def test_missing_when_claim_but_no_test(self, tmp_path):
        item = BacklogItem(
            title="Some bug",
            section="High",
            raw_text="Fixed via PR #99",
            resolution_claims=[
                ResolutionClaim(
                    claim_type=ClaimType.PR, evidence_text="PR #99", pr_number=99
                )
            ],
        )
        result = classify_item(item, [], tmp_path)
        assert result.status == AuditStatus.MISSING

    def test_provisional_green_when_test_paths_present(self, tmp_path):
        fake_test = tmp_path / "test_x.py"
        fake_test.write_text("def test_x(): pass\n")
        item = BacklogItem(
            title="Some bug",
            section="High",
            raw_text="Fixed via PR #99",
            resolution_claims=[
                ResolutionClaim(
                    claim_type=ClaimType.PR, evidence_text="PR #99", pr_number=99
                )
            ],
        )
        result = classify_item(item, [fake_test], tmp_path)
        assert result.status == AuditStatus.GREEN

    def test_unverifiable_when_no_resolution_claim(self, tmp_path):
        item = BacklogItem(
            title="Open work item",
            section="High",
            raw_text="- something to do\n- not yet started",
            resolution_claims=[],
        )
        result = classify_item(item, [], tmp_path)
        assert result.status == AuditStatus.UNVERIFIABLE


# ─── CLI exit code tests (via main()) ──────────────────────────────────────


class TestCLIExitCodes:
    def test_exit_2_when_backlog_missing(self, tmp_path, capsys):
        rc = _module.main(["--backlog", str(tmp_path / "nonexistent.md")])
        assert rc == 2

    def test_exit_0_on_clean_fixture(self, tmp_path):
        backlog = tmp_path / "backlog.md"
        backlog.write_text(
            "## Completed\n\n### Already Done Item\n- Status: DONE in v1.0\n"
        )
        rc = _module.main(
            [
                "--backlog",
                str(backlog),
                "--mode",
                "no-run",
                "--sections",
                "Completed",
                "--check-completed",
                "--output",
                str(tmp_path / "report.md"),
            ]
        )
        assert rc == 0  # All items SKIPPED → no actionable

    def test_exit_1_on_missing_test(self, tmp_path):
        backlog = tmp_path / "backlog.md"
        backlog.write_text("## High\n\n### Some Bug\n- Fixed via PR #99\n")
        tests_root = tmp_path / "tests"
        tests_root.mkdir()
        rc = _module.main(
            [
                "--backlog",
                str(backlog),
                "--tests-root",
                str(tests_root),
                "--mode",
                "no-run",
                "--output",
                str(tmp_path / "report.md"),
            ]
        )
        assert rc == 1
