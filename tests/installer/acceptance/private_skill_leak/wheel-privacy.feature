# Concern 1 (wheel privacy) + Concern 2 (public skill survival).
#
# The public PyPI wheel must carry only public artifacts, and the privacy
# strip must not drop public skills that public artifacts depend on.
#
# The slice-01 WALKING SKELETON for this contract is NOT in this file — it
# is the genuine end-to-end test at
# ``tests/e2e/test_wheel_private_artifact_contract.py``. That test builds a
# real ``.whl`` through the release pipeline (build_dist.py ->
# patch_pyproject.py -> python -m build --wheel), unzips it, and inspects
# the archive a customer actually receives. The earlier in-process
# ``@walking_skeleton`` scenario stripped a tree the test itself copied —
# it verified the strip FUNCTION, never the release ARTIFACT, and was a
# false GREEN by construction. It has been removed.
#
# The scenarios below are FOCUSED BOUNDARY checks of the strip function
# (layer-3 real-filesystem tree strip, ~100ms). They are fast feedback for
# the strip's set-theoretic behaviour (idempotency, public/private
# partition); the real-wheel guarantee is the e2e walking skeleton.

@feature-fix-installer-private-skill-leak @concern-1 @concern-2
Feature: The public package excludes private work and keeps public work

  As the maintainer of the public nwave-ai package
  I want the published package to carry only public artifacts
  So that internal work is never disclosed and public installs never break

  Background:
    Given the nWave framework source with private agents and skills

  @slice-02 @driving_port @real-io @contract-shape:unbounded-preservation
  Scenario: The release gate refuses a package that still carries private work
    Given a package that was prepared without removing private work
    When the release privacy gate inspects that package
    Then the release privacy gate reports the private work it found
    And the release privacy gate refuses to pass

  @slice-02 @driving_port @real-io @contract-shape:unbounded-preservation
  Scenario: The release gate passes a package that carries only public work
    Given a package that was prepared with private work removed
    When the release privacy gate inspects that package
    Then the release privacy gate reports no private work
    And the release privacy gate passes

  @slice-01 @driving_port @real-io @contract-shape:bounded-change
  Scenario: Preparing the public package a second time yields the same result
    Given a package that was prepared with private work removed
    When the public package is prepared for release again from that package
    Then the twice-prepared package contains no private agent
    And the twice-prepared package contains no private skill
    And the twice-prepared package still contains every public skill a public artifact depends on

  @slice-01 @driving_port @real-io @contract-shape:bounded-change
  Scenario: Preparing the public package removes private work and keeps the rest
    When the public package is prepared for release
    Then the prepared package keeps every public agent
    And the prepared package removes every private agent
    And the prepared package keeps every public skill a public artifact depends on
