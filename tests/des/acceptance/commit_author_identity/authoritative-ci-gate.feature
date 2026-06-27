# Feature: Commit author/committer identity validation — authoritative CI gate
# Design source: docs/feature/commit-author-identity-validation/plan.md (DESIGN Layer C + regression anchor)
#                docs/analysis/commit-author-validation-research.md §3.1, §3.2
# Layer: 3 (pure-Python CI runner driven over a real git range in an isolated repo;
#           NOT a live GitHub Actions run — Mandate 9 + 11, example-based)
# Tier: A (production composition root)

Feature: The unbypassable gate catches placeholder identities in a change set
  As a maintainer who cannot trust local hooks to always run
  I want an authoritative gate that inspects every commit in a proposed change set
  So that placeholder identities are caught even when local hooks were skipped

  # ── CI walking skeleton ─────────────────────────────────────────────
  # The authoritative gate survives --no-verify and disabled local hooks
  # (research §3.1) — it is the gate that actually protects the trunk.

  @walking_skeleton @driving_port @contract-shape:unbounded-preservation @ci @error
  Scenario: A change set containing a placeholder author is flagged by the authoritative gate
    Given a fresh repository
    When a placeholder-authored commit reaches the range by skipping the commit gate
    And the authoritative gate inspects the whole change set
    Then the change set is flagged

  # ── CI happy path ───────────────────────────────────────────────────

  @driving_port @contract-shape:unbounded-preservation @ci
  Scenario: A change set of clean commits is cleared by the authoritative gate
    Given a fresh repository
    When a clean commit is added to the range
    And the authoritative gate inspects the whole change set
    Then the change set is cleared

  # ── Committer-side placeholder caught by the authoritative gate ─────

  @driving_port @contract-shape:unbounded-preservation @ci @error
  Scenario: A change set containing a placeholder committer is flagged by the authoritative gate
    Given a fresh repository
    When a commit with a "PLACEHOLDER_T_AT_T" committer reaches the range
    And the authoritative gate inspects the whole change set
    Then the change set is flagged

  # ── Regression anchor — the real failing instance (plan.md) ─────────
  # PR #42 carried 8 commits authored test@example.com. This is THE
  # instance the whole feature exists to catch. Marked as the regression
  # anchor so DELIVER verifies the gate flags it before claiming the fix.

  @regression_anchor @driving_port @contract-shape:unbounded-preservation @ci @error
  Scenario: The change set equivalent to the real placeholder-authored pull request is flagged
    Given a fresh repository
    When a change set equivalent to the eight placeholder-authored commits is proposed
    And the authoritative gate inspects the whole change set
    Then the change set is flagged
    And every offending commit in the change set is named in the report

  # ── First commit clean, a later commit placeholder (H1) ─────────────
  # Guards against a `rows[:1]`-style regression that would only inspect the
  # first commit: here the first commit is clean and the placeholder is later.

  @driving_port @contract-shape:unbounded-preservation @ci @error
  Scenario: A change set whose first commit is clean but a later commit is a placeholder is flagged
    Given a fresh repository
    When a change set whose first commit is clean but a later commit is a placeholder
    And the authoritative gate inspects the whole change set
    Then the change set is flagged
    And every offending commit in the change set is named in the report

  # ── Single pushed commit with no range (W1 degrade-to-HEAD) ─────────
  # A push event can arrive with no base..head range (initial push,
  # force-push, or an unfetched parent): the gate is invoked over HEAD
  # alone. "No range" must never mean "no validation" — the gate still
  # inspects the single pushed commit (ci_author_check W1, research §3.2).

  @driving_port @contract-shape:unbounded-preservation @ci @error
  Scenario: A single pushed commit carrying a placeholder author is flagged when no range is given
    Given a fresh repository
    When a single "PLACEHOLDER_TEST_EXAMPLE" commit is pushed with no range
    Then the change set is flagged
    And every offending commit in the change set is named in the report

  @driving_port @contract-shape:unbounded-preservation @ci
  Scenario: A single clean pushed commit is cleared when no range is given
    Given a fresh repository
    When a single "NOREPLY_PLAIN" commit is pushed with no range
    Then the change set is cleared

  # ── Authoritative gate validates NAMES, not emails alone (R3-F1) ────
  # The unbypassable gate is the one that backstops --no-verify and a
  # hooksPath injection. If it checks only emails, a placeholder NAME with a
  # valid email walks straight onto the trunk. The gate must flag a
  # placeholder author or committer name across the whole change set.

  @driving_port @contract-shape:bounded-change @ci @error
  Scenario: A change set whose author name is a placeholder is flagged by the authoritative gate
    Given a fresh repository
    When a commit under the author name class "NAME_TEST_CAPITAL" reaches the range
    And the authoritative gate inspects the whole change set
    Then the change set is flagged

  @driving_port @contract-shape:bounded-change @ci @error
  Scenario: A change set whose committer name is a placeholder is flagged by the authoritative gate
    Given a fresh repository
    When a commit under the committer name class "NAME_USER" reaches the range
    And the authoritative gate inspects the whole change set
    Then the change set is flagged

  # ── Single-commit / --head-only degrade path validates the NAME (R3-F1)
  # A push event with no base..head range invokes the gate over HEAD alone.
  # The NAME check must run there too: a single pushed commit carrying a
  # placeholder author name and a clean email must be flagged.

  @driving_port @contract-shape:bounded-change @ci @error
  Scenario: A single pushed commit carrying a placeholder author name is flagged when no range is given
    Given a fresh repository
    When a single commit under the author name class "NAME_TEST_CAPITAL" is pushed with no range
    Then the change set is flagged
