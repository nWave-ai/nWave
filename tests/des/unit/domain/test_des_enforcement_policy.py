"""Unit tests for DES Enforcement Policy.

Tests the step-id based enforcement rule:
- Task prompts containing step-id patterns (\\d{2}-\\d{2}) without DES markers get blocked
- Prompts with DES markers pass through
- Prompts without step-id patterns pass through
- ISO dates are not false positives
"""

import pytest

from des.domain.des_enforcement_policy import DesEnforcementPolicy


class TestDesEnforcementPolicy:
    """Unit tests for DesEnforcementPolicy."""

    @pytest.fixture
    def policy(self):
        return DesEnforcementPolicy()

    def test_step_id_without_markers_is_enforced(self, policy):
        """Task prompt with step-id but no DES markers should be blocked."""
        result = policy.check("Execute step 01-01 for the authentication feature")
        assert result.is_enforced is True
        assert result.reason is not None
        assert "01-01" in result.reason

    def test_step_id_with_markers_not_enforced(self, policy):
        """Task prompt with step-id AND DES-VALIDATION marker should pass."""
        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            "<!-- DES-PROJECT-ID : auth-upgrade -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            "Execute step 01-01"
        )
        result = policy.check(prompt)
        assert result.is_enforced is False

    def test_no_step_id_not_enforced(self, policy):
        """Task prompt without step-id pattern should pass (research task)."""
        result = policy.check("Research authentication best practices for the project")
        assert result.is_enforced is False

    def test_exempt_marker_bypasses_enforcement(self, policy):
        """Task prompt with exempt marker should pass even with step-id."""
        prompt = (
            "<!-- DES-ENFORCEMENT : exempt -->\n"
            "Review roadmap step 01-01 for completeness"
        )
        result = policy.check(prompt)
        assert result.is_enforced is False

    def test_enforced_reason_contains_detected_step_id(self, policy):
        """Block reason should include the detected step-id."""
        result = policy.check("Implement step 02-03 changes")
        assert result.is_enforced is True
        assert "02-03" in (result.reason or "")

    def test_recovery_suggestions_contain_marker_template(self, policy):
        """Recovery suggestions should include DES-VALIDATION marker template."""
        result = policy.check("Execute step 01-01")
        assert result.is_enforced is True
        assert any("DES-VALIDATION" in s for s in result.recovery_suggestions)

    def test_empty_prompt_not_enforced(self, policy):
        """Empty prompt should pass (no step-id to detect)."""
        result = policy.check("")
        assert result.is_enforced is False

    def test_iso_date_not_false_positive(self, policy):
        """ISO date like '2026-02-09' should not trigger enforcement."""
        result = policy.check("Deploy by 2026-02-09 deadline for the release")
        assert result.is_enforced is False
