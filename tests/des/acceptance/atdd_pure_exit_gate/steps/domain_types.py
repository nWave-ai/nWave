"""Domain types for the slice-14 G_COMMIT exit-gate acceptance slice.

slice-14 of the atdd-pure-roadmap-free-rollout (Mandate-12 criterion 1). Every
domain noun used in the Gherkin is expressed once here as a typed enum or
NewType. Step bodies and the composition service consume these typed parameters
-- no raw `str` where a domain enum exists.

The slice ships a DES `exit_gate` on `G_COMMIT` with two assertions:
  E1 -- slice-commit completeness: the committed file set contains the slice's
        `.feature` AT files (RCA Branch A).
  E2 -- terminating run == contract gate: a `Gate-Scope:` digest is present and
        matches a fresh `run_contract_gate.py --collect-only` digest (RCA
        Branch B).
"shipped" is then derivable from the exit gate passing, not agent prose (RCA
Branch C).
"""

from __future__ import annotations

from enum import Enum
from typing import NewType


# A kebab-case feature identifier (e.g. "atdd-pure-demo").
FeatureId = NewType("FeatureId", str)

# A slice identifier as carried by a `Slice-Id:` / `Step-Id:` commit trailer
# (e.g. "slice-14").
SliceId = NewType("SliceId", str)


class CommitFeatureContent(str, Enum):
    """What the slice's `G_COMMIT` commit actually contains, AT-file-wise.

    The slice-commit completeness assertion (E1) inspects the committed file
    set via `git show --name-only` and requires every `@slice-NN` scenario to
    live in a git-tracked `.feature` file that is either present in this commit
    or already tracked and unmodified by this slice.

    AT_FILES_INCLUDED  -- the commit stages the slice's `.feature` AT files
                          alongside the production code. The honest deliverable.
    AT_FILES_MISSING   -- the commit stages production code only; the slice's
                          `.feature` files were authored in a working tree
                          state never persisted. The exact RCA Branch-A defect
                          (fa6ddc1d0 shipped `init_log.py` with no ATs).
    """

    AT_FILES_INCLUDED = "at_files_included"
    AT_FILES_MISSING = "at_files_missing"


class GateScopeDigestState(str, Enum):
    """The state of the `Gate-Scope:` digest the `G_COMMIT` commit carries.

    `run_contract_gate.py` runs `pytest -m "unit or integration or acceptance"`
    over the whole tree and emits a `gate_scope_digest` -- the sorted set of
    collected test node-ids, hashed. The exit gate (E2) re-derives a fresh
    digest via `run_contract_gate.py --collect-only` and compares.

    MATCHING  -- the commit carries a `Gate-Scope:` digest equal to a fresh
                 `--collect-only` digest. The terminating run WAS the contract
                 gate.
    MISMATCH  -- the commit carries a `Gate-Scope:` digest that does NOT match
                 a fresh digest (a stale digest, or a digest from a narrower
                 crafter-picked subset run -- the RCA Branch-B defect).
    ABSENT    -- the commit carries no `Gate-Scope:` trailer / ledger record at
                 all. Verification scope is unverified.
    """

    MATCHING = "matching"
    MISMATCH = "mismatch"
    ABSENT = "absent"


class ExitGateVerdict(str, Enum):
    """The user-observable verdict of the `G_COMMIT` DES exit gate.

    PASS  -- both assertions held; the slice may reach COMMIT/PASS in the DES
             execution record. "shipped" is mechanically derivable.
    FAIL  -- at least one assertion failed; DES blocks `G_COMMIT` phase
             completion. The commit is refused, the slice cannot be declared
             shipped.
    """

    PASS = "pass"
    FAIL = "fail"


# Gherkin-phrase -> typed-value lookups. Keeping these as module-level dicts
# lets each step body stay a single typed lookup + a single composition call
# (Mandate-12 criterion 3: no control flow in step bodies).

COMMIT_CONTENT_BY_PHRASE: dict[str, CommitFeatureContent] = {
    "includes the slice's acceptance-test files": CommitFeatureContent.AT_FILES_INCLUDED,
    "is missing the slice's acceptance-test files": CommitFeatureContent.AT_FILES_MISSING,
}

DIGEST_STATE_BY_PHRASE: dict[str, GateScopeDigestState] = {
    "matching": GateScopeDigestState.MATCHING,
    "mismatching": GateScopeDigestState.MISMATCH,
    "absent": GateScopeDigestState.ABSENT,
}

VERDICT_BY_PHRASE: dict[str, ExitGateVerdict] = {
    "passes": ExitGateVerdict.PASS,
    "fails": ExitGateVerdict.FAIL,
}
