# Feature: Commit author/committer identity validation — local gates
# Design source: docs/feature/commit-author-identity-validation/plan.md (DESIGN, Layers A+B)
#                docs/analysis/commit-author-validation-research.md §2.4 (pre-commit), §2.5 (pre-push)
# Layer: 3 (real git in an isolated tmp repo, example-based — Mandate 9 + 11)
# Tier: A (production composition root; isolated git repo is the one environment substitution)

Feature: Local gates stop placeholder identities before they enter shared history
  As a contributor committing and pushing work
  I want my commit to be refused the moment its author or committer identity
    is a placeholder or misconfiguration
  So that I fix the identity locally instead of polluting shared history

  # ── pre-commit walking skeleton ─────────────────────────────────────

  @walking_skeleton @driving_port @contract-shape:unbounded-preservation @precommit @error
  Scenario: A commit authored by a placeholder identity is refused at commit time
    Given a fresh repository
    When a contributor commits with a "PLACEHOLDER_TEST_EXAMPLE" author
    And the pre-commit identity gate runs
    Then the commit is refused
    And the contributor is told which identity field was rejected

  # ── pre-commit happy path ───────────────────────────────────────────

  @driving_port @contract-shape:unbounded-preservation @precommit
  Scenario: A commit authored by a GitHub anonymous identity is allowed at commit time
    Given a fresh repository
    When a contributor commits with a "NOREPLY_PLAIN" author
    And the pre-commit identity gate runs
    Then the commit is allowed

  # ── degraded environment: identity cannot be resolved (C7a / research §2.4)
  # When no identity is configured at all and git refuses to guess one, the
  # gate must fail loudly rather than admit an unattributed commit.

  @driving_port @contract-shape:unbounded-preservation @precommit @error @degraded-environment
  Scenario: A commit is refused when no identity can be resolved at all
    Given a fresh repository
    When the contributor has no resolvable commit identity
    And the pre-commit identity gate runs
    Then the commit is refused
    And the contributor is told which identity field was rejected

  # ── author and committer checked independently (research §2.2) ──────
  # A diverging pair: one role allowlisted, the other a placeholder.

  @driving_port @contract-shape:unbounded-preservation @precommit @error
  Scenario: A clean author cannot smuggle a placeholder committer past the gate
    Given a fresh repository
    When a contributor commits with a "PLACEHOLDER_T_AT_T" committer
    And the pre-commit identity gate runs
    Then the commit is refused
    And the contributor is told which identity field was rejected

  @driving_port @contract-shape:unbounded-preservation @precommit @error
  Scenario: A clean committer cannot smuggle a placeholder author past the gate
    Given a fresh repository
    When a contributor commits with a "EXAMPLE_COM" author
    And the pre-commit identity gate runs
    Then the commit is refused

  # ── pre-commit name check (H2) ──────────────────────────────────────
  # A placeholder NAME with a perfectly valid email must still be refused —
  # the name field is checked independently of the email.

  @driving_port @contract-shape:unbounded-preservation @precommit @error
  Scenario: A commit under a placeholder author name is refused even with a valid email
    Given a fresh repository
    When a contributor commits under the author name class "NAME_TEST_CAPITAL"
    And the pre-commit identity gate runs
    Then the commit is refused
    And the contributor is told which identity field was rejected

  # ── pre-push walking skeleton — catches a bypassed commit (research §2.7)
  # The push gate inspects the whole range, so a commit that skipped the
  # local commit-time gate is still caught before it leaves the machine.

  @walking_skeleton @driving_port @contract-shape:unbounded-preservation @prepush @error
  Scenario: A pushed range containing a bypassed placeholder commit is refused
    Given a fresh repository
    When a placeholder-authored commit reaches the range by skipping the commit gate
    And the pre-push identity gate inspects an existing upstream range
    Then the push is refused

  # ── pre-push happy path ─────────────────────────────────────────────

  @driving_port @contract-shape:unbounded-preservation @prepush
  Scenario: A pushed range of clean commits is allowed
    Given a fresh repository
    When a clean commit is added to the range
    And the pre-push identity gate inspects an existing upstream range
    Then the push is allowed

  # ── pre-push new-branch zero-SHA case (research §2.5) ───────────────
  # A brand-new branch has no upstream; the remote object name is the zero
  # SHA. The gate must still validate every commit not yet on any remote.

  @driving_port @contract-shape:unbounded-preservation @prepush @error
  Scenario: A brand-new branch with a placeholder commit is refused
    Given a fresh repository
    When a placeholder-authored commit reaches the range by skipping the commit gate
    And the pre-push identity gate inspects a brand-new branch with no upstream
    Then the push is refused

  @driving_port @contract-shape:unbounded-preservation @prepush
  Scenario: A brand-new branch of clean commits is allowed
    Given a fresh repository
    When a clean commit is added to the range
    And the pre-push identity gate inspects a brand-new branch with no upstream
    Then the push is allowed

  # ── pre-push committer-side placeholder (H3) ────────────────────────
  # The push gate validates the COMMITTER email too, not only the author.

  @driving_port @contract-shape:unbounded-preservation @prepush @error
  Scenario: A pushed range whose committer is a placeholder is refused
    Given a fresh repository
    When a commit with a "PLACEHOLDER_T_AT_T" committer reaches the range
    And the pre-push identity gate inspects an existing upstream range
    Then the push is refused

  # ── pre-push bypass: placeholder commit already on another branch (M1)
  # `--not --remotes` subtracts any commit already reachable from a remote
  # ref. A placeholder commit that was previously pushed to another branch
  # is therefore EXCLUDED from a new-branch push range — yet introducing it
  # into this branch's history must still be refused.

  @driving_port @contract-shape:unbounded-preservation @prepush @error
  Scenario: A placeholder commit already published on another branch is still refused on a new-branch push
    Given a fresh repository
    When a placeholder commit is already published on another branch
    And the pre-push identity gate inspects a brand-new branch with no upstream
    Then the push is refused

  # ── pre-push robustness: tab in author name (M2) ────────────────────
  # A tab inside the author NAME misaligns the `%H\t%an\t%ae\t%ce` column
  # split, so the runner reads the wrong field and the placeholder author
  # email is never reported AS a placeholder. The push must be refused AND
  # the offending author email named as the placeholder it is.

  @driving_port @contract-shape:unbounded-preservation @prepush @error
  Scenario: A placeholder author email hidden behind a tab in the name is named as a placeholder
    Given a fresh repository
    When a contributor hides a placeholder author email behind a tab in the name
    And the pre-push identity gate inspects an existing upstream range
    Then the push is refused
    And the rejection names the placeholder author email as a placeholder

  # ── pre-push NAME validation (R3-F1) ────────────────────────────────
  # The push gate validates author AND committer NAMES, not emails alone. A
  # placeholder name with a perfectly valid email must still be refused —
  # the only gate that backstops --no-verify / hooksPath injection cannot
  # afford to skip the name field the pre-commit gate already checks.

  @driving_port @contract-shape:bounded-change @prepush @error
  Scenario: A pushed range whose author name is a placeholder is refused
    Given a fresh repository
    When a commit under the author name class "NAME_TEST_CAPITAL" reaches the range
    And the pre-push identity gate inspects an existing upstream range
    Then the push is refused
    And the contributor is told which identity field was rejected

  @driving_port @contract-shape:bounded-change @prepush @error
  Scenario: A pushed range whose committer name is a placeholder is refused
    Given a fresh repository
    When a commit under the committer name class "NAME_USER" reaches the range
    And the pre-push identity gate inspects an existing upstream range
    Then the push is refused
    And the contributor is told which identity field was rejected

  # ── pre-push NAME robustness — tab in the name (R3-F1, critical) ────
  # Once the runner reads %an/%cn, a TAB inside the name must NOT misalign a
  # column split. Two faithful vectors git permits in a stored commit:
  #  (1) the name itself is a placeholder hidden behind a tab → still caught;
  #  (2) a tab in the name hides a placeholder EMAIL behind a clean-looking
  #      fragment → the real placeholder email is still read on the author field.

  @driving_port @contract-shape:bounded-change @prepush @error @robustness
  Scenario: A placeholder author name hidden behind a tab in the name is still refused and named
    Given a fresh repository
    When a contributor hides a placeholder author name behind a tab in the name
    And the pre-push identity gate inspects an existing upstream range
    Then the push is refused
    And the rejection names the placeholder author name as a placeholder

  @driving_port @contract-shape:bounded-change @prepush @error @robustness
  Scenario: A tab in the name cannot smuggle a placeholder author email past the push gate
    Given a fresh repository
    When a contributor hides a placeholder author email behind a tab in the range name
    And the pre-push identity gate inspects an existing upstream range
    Then the push is refused
    And the rejection names the placeholder author email as a placeholder

  # ── pre-push fail-closed when no default branch resolves (R3-F4) ────
  # On a new-branch push where NO origin/* ref resolves, the runner must
  # fall back to validating the whole reachable set rather than skipping —
  # a placeholder anywhere in that history is still refused.

  @driving_port @contract-shape:unbounded-preservation @prepush @error
  Scenario: A new-branch push with no resolvable default branch still refuses a placeholder
    Given a fresh repository
    When the pre-push identity gate inspects a new branch with no default branch to compare against
    Then the push is refused
