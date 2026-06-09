"""Step definitions: nw-execute / nw-continue orchestration docs branch on mode.

ADR-028 D6 / slice-08 of the atdd-pure-roadmap-free-rollout (feature-delta
``### slice-08`` design note, L685-725).

Layer 3 (FS-reading coherence). Example-only, no PBT machinery (Mandate 9/11):
the slice-08 contract clauses are a closed enumerable set, realised as three
``Scenario Outline``s, NOT a Hypothesis @given.

Step bodies delegate to ``ExecuteContinueCoherenceComposition``; no inline
business logic (Mandate-12 criterion 3) -- each body is a typed lookup plus a
composition call or a single assertion over a composition-computed value.

Regression contract: every NEW and MODE_SCOPED scenario FAILS on master and
PASSES once slice-08 lands. On master the four orchestration docs
(``nw-execute/SKILL.md``, ``nw-continue/SKILL.md``, ``nw/execute.md``,
``nw/continue.md``) are mode-unaware -- no ``workflow.mode`` branch, no
``atdd_pure`` path, no ``carpaccio`` / ``per-slice lean cycle`` / ``A_GREEN_ATS``
vocabulary, no ``un-shipped slice`` / ``FeatureEndCheckpoint`` resume cue -- and
they mention ``roadmap.json`` / ``execution-log`` on lines carrying no
``classic`` / ``workflow.mode`` qualifier. Each NEW clause's master-absent
token is verified absent on master and each MODE_SCOPED clause's master-present
token verified present-and-unscoped, so these are genuine
missing-functionality RED, not test bugs.

See the acceptance brief WAVE: DISTILL section for the Class-typing +
testable-surface finding and the design-note discrepancy (the continue pair
carries an execution-log MODE_SCOPED clause ONLY, no roadmap.json clause --
roadmap.json is 0 on master nw-continue, a roadmap clause there would be
vacuously satisfied).
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from .composition import ClauseVerdict, ExecuteContinueCoherenceComposition
from .domain_types import (
    CONTINUE_NEW_CLAUSE_BY_PHRASE,
    DOC_BY_PHRASE,
    EXECUTE_NEW_CLAUSE_BY_PHRASE,
    MODE_SCOPED_TOKEN_BY_PHRASE,
    ClauseKind,
)


scenarios("../nw-execute-continue-mode-coherence.feature")


# --- Given -------------------------------------------------------------------


@given(
    parsers.parse("{orchestration_doc_phrase}"),
    target_fixture="composition",
)
def given_orchestration_doc(
    orchestration_doc_phrase: str,
) -> ExecuteContinueCoherenceComposition:
    # orchestration_doc_phrase is a closed-set key -- every phrase used in a
    # Given / Scenario-Outline doc column ("the nw-execute skill", ...) is
    # registered in DOC_BY_PHRASE. A missing key would KeyError (the slice-04
    # step-resolution defect), caught by the collect-only + real-run gate.
    doc = DOC_BY_PHRASE[orchestration_doc_phrase]
    composition = ExecuteContinueCoherenceComposition()
    composition.load_doc(doc)
    return composition


# --- When --------------------------------------------------------------------


@when("the orchestration doc is read for the atdd_pure project mode")
def when_read_atdd_pure(composition: ExecuteContinueCoherenceComposition) -> None:
    # The SUT (the doc content) is mode-independent text; the mode here records
    # intent for the chained narrative (Pillar 2). No-op against the
    # already-loaded composition -- the assertion confirms a Given ran.
    assert composition._doc_text


@when("the orchestration doc is read for the classic project mode")
def when_read_classic(composition: ExecuteContinueCoherenceComposition) -> None:
    assert composition._doc_text


# --- Then --------------------------------------------------------------------


@then(
    parsers.parse("the execute orchestration doc {execute_clause_phrase}"),
    target_fixture="verdict",
)
def then_execute_clause_satisfied(
    composition: ExecuteContinueCoherenceComposition,
    execute_clause_phrase: str,
) -> ClauseVerdict:
    # The execute-pair NEW Scenario Outline. execute_clause_phrase is a
    # closed-set key in EXECUTE_NEW_CLAUSE_BY_PHRASE. The doc is the single doc
    # loaded by this scenario's Given (the outline runs one doc per row).
    clause = EXECUTE_NEW_CLAUSE_BY_PHRASE[execute_clause_phrase]
    doc = composition.sole_loaded_doc()
    verdict = composition.evaluate_clause(doc, clause.value)
    assert verdict.satisfied, (
        f"{doc.value} does not satisfy the execute-pair clause "
        f"'{clause.value}' ({verdict.kind.value}) -- slice-08 has not landed"
    )
    return verdict


@then(
    parsers.parse("the continue orchestration doc {continue_clause_phrase}"),
    target_fixture="verdict",
)
def then_continue_clause_satisfied(
    composition: ExecuteContinueCoherenceComposition,
    continue_clause_phrase: str,
) -> ClauseVerdict:
    # The continue-pair NEW Scenario Outline. continue_clause_phrase is a
    # closed-set key in CONTINUE_NEW_CLAUSE_BY_PHRASE.
    clause = CONTINUE_NEW_CLAUSE_BY_PHRASE[continue_clause_phrase]
    doc = composition.sole_loaded_doc()
    verdict = composition.evaluate_clause(doc, clause.value)
    assert verdict.satisfied, (
        f"{doc.value} does not satisfy the continue-pair clause "
        f"'{clause.value}' ({verdict.kind.value}) -- slice-08 has not landed"
    )
    return verdict


@then("that contract clause is new relative to the mode-unaware master doc")
def then_clause_is_new(verdict: ClauseVerdict) -> None:
    # This step runs only on the two NEW-clause Scenario Outlines. Guard the
    # contract: a clause reaching this assertion MUST be ClauseKind.NEW -- a
    # MODE_SCOPED clause asserts a per-line qualification, not a newness, and a
    # PRESERVATION clause has no honest new-vs-master delta; neither must ever
    # be asserted "new" (slice-04 review Blocking 1).
    assert verdict.kind is ClauseKind.NEW, (
        f"clause '{verdict.clause}' is a {verdict.kind.value} clause -- only "
        f"NEW clauses carry a new-vs-master regression signal"
    )
    assert verdict.regressed_from_master, (
        f"the master-absent token for clause '{verdict.clause}' is not in "
        f"{verdict.doc.value} -- this clause cannot be a slice-08 regression "
        f"signal"
    )


@then(
    parsers.parse(
        "every line mentioning {legacy_artifact_phrase} is scoped to a workflow mode"
    )
)
def then_legacy_artifact_mode_scoped(
    composition: ExecuteContinueCoherenceComposition,
    legacy_artifact_phrase: str,
) -> None:
    # The MODE_SCOPED Scenario Outline. legacy_artifact_phrase is a closed-set
    # key in MODE_SCOPED_TOKEN_BY_PHRASE -> the audited token ("roadmap.json"
    # / "execution-log"). The clause id is derived from the token: both the
    # execute pair and the continue pair name the clause
    # "<token>_references_mode_scoped" via the *_REFERENCES_MODE_SCOPED enum
    # members, whose .value strings are constructed below.
    token = MODE_SCOPED_TOKEN_BY_PHRASE[legacy_artifact_phrase]
    clause_id = (
        "roadmap_references_mode_scoped"
        if token == "roadmap.json"
        else "execution_log_references_mode_scoped"
    )
    doc = composition.sole_loaded_doc()
    verdict = composition.evaluate_clause(doc, clause_id)
    assert verdict.kind is ClauseKind.MODE_SCOPED, (
        f"clause '{clause_id}' on {doc.value} is a {verdict.kind.value} "
        f"clause -- the mode-scoping assertion applies only to MODE_SCOPED"
    )
    assert verdict.satisfied, (
        f"{doc.value} mentions '{token}' on unscoped line(s) "
        f"{list(verdict.unscoped_lines)} -- no classic / workflow.mode "
        f"qualifier on those lines; slice-08 has not mode-scoped them"
    )
