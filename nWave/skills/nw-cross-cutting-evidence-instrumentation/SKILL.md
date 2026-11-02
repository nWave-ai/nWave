---
name: nw-cross-cutting-evidence-instrumentation
description: KNOWLEDGE — use when evaluating a claim, check, measurement, or shared-log count.
user-invocable: false
disable-model-invocation: true
---

# Evidence and Instrumentation

**Composition:** Load with `nw-cross-cutting-invariants`; no forced sequence; return to its routing table for other concerns.

## `claim:falsify-before-asserting` — the cheapest check precedes the conclusion (STANDING)

Before concluding that something cannot work, is missing, or is broken, run the cheapest check
that would falsify that conclusion, then state only what the check showed. Name a cause only if
you observed it — never infer one from a shared symptom. Absence in one place is not absence in
the tree: measure on the scope the claim is actually ABOUT, not the subset you happened to look
at (the enumerator gap above is the architectural form of this same failure). The asymmetry that
justifies the discipline: the check costs seconds; an unfalsified conclusion, once acted on,
costs an order of magnitude more to undo.

## `check:unfired-is-not-evidence` — a check you have not seen FAIL is not evidence (STANDING)

A passing check has two indistinguishable explanations: the property holds, or the check cannot
detect its violation. Green discriminates between them only AFTER the check has been observed
failing on a constructed violation. Before that, green is a fact about the instrument, not about
the subject.

Binds every instrument, not only tests:

| Instrument | Vacuous when | What earns the trust |
|---|---|---|
| negative test | the corruption is applied where the subject is not | corrupt AT the subject's own locus; watch the assertion fire |
| guard predicate | the pattern accepts the empty case (`^password=` matches an empty value) | feed the empty and near-miss forms; watch both rejected |
| gate | its arming precondition is absent, so it skips | run it on an artifact that violates the rule; watch the refusal |
| oracle inside an AT | the step derives the value it was supposed to read from the output | withhold the field; watch the step fail |

The demonstration is an ACT, never an argument: "this would obviously catch it" is the reasoning
that produced every vacuous check already shipped. Cost asymmetry — constructing the violation
costs one run; a vacuous check ships as coverage and every later reader reads its green as proof.

**Who demonstrates it, and when: the AUTHOR, immediately, with no dispatch.** Whoever writes the
check, tool, gate or script runs it against a constructed violation right after writing it and
watches HOW it fails.

**This clause governs WHO RUNS the demonstration. It says nothing about WHO WRITES the code, and
conflating the two licenses hand-authoring production code.** The two rules are orthogonal and both
bind: authorship of production code follows the dispatch discipline, while the fail-demonstration is
always the author's own act, executed on the spot. So "demonstrate it yourself, no dispatch" is an
instruction about the demonstration only — a dispatched implementer still runs its own
demonstration, and an orchestrator who reads that phrase as permission to write the code has taken
a licence the clause does not grant. Anyone handed the shorter phrasing and noticing the collision
should say so rather than pick a side silently. That is seconds of work at the authoring surface; routing it to an independent
examiner buys nothing here and costs a full handoff, because the question — *can this instrument
fire?* — is decided by execution, and the author is already holding the keyboard. Reserve an
independent reader for the different question: whether the number MEANS what the report claims.

Corollary: the FIRST version of a measuring instrument is suspect BY CONSTRUCTION — it is the only
version written before its author has seen the data, and a test written from that same first reading
inherits the misreading it was built to catch. Green unit tests certify the arithmetic the instrument
was told to do, never that the figure means what the report says it means. The check worth writing is
the one that could embarrass you.

## `instrument:a-reading-that-misled-you-is-a-defect-in-the-instrument` — fix the tool, not the conclusion (STANDING)

When a measurement, receipt or status report leads to a wrong action, the finding is not "I should
read it more carefully next time". The instrument is defective and the work is to REPAIR IT — vigilance
does not scale, and the next reader inherits the same trap with less context than you had.

| Step | What it means |
|---|---|
| Name the axis that lied | not "it was wrong" — WHICH signal, and what it actually measures versus what you read it as |
| Repair the instrument | and prefer removing the inference over adding a caveat: a footnote is not a fix |
| Re-run it on the case that fooled you | the repair is verified by the original counterexample reproducing the correct answer, never by the code looking better |
| Keep the counterexample | in the instrument, as a comment or a test, so the next change cannot silently restore the trap |

Two failure shapes this rule exists to stop, both observed:

- **Fixing the conclusion instead of the tool.** Correcting the one wrong verdict and leaving the
  instrument intact guarantees the same wrong verdict, and the second occurrence looks like a fresh
  mistake rather than a known one.
- **Fixing the wrong axis.** Diagnose before repairing: an instrument can produce the right complaint
  from the wrong cause, and a plausible repair then leaves the real defect in place while retiring
  the symptom that would have exposed it. Establish which signal failed by reproducing it, not by
  reasoning about which signal COULD have failed — the two diverge, and the second is faster to
  produce and satisfying to believe.

Corollary — **an instrument you run repeatedly is production code.** A report generated on a schedule
or before every decision does not get to live as an unversioned scratch script: it needs a home, a
history, and a test, because a defect in it is a defect in every decision downstream of it.

Corollary — **the guidance corpus is an instrument, and it is usually the one that failed.**
The rows above read naturally as being about measurements and receipts. They are not limited to
them: a skill, mandate, agent spec or command prose that let a defect through is a defective
instrument in exactly the same sense, and the repair is to change that prose — never a resolution
to remember harder next time.

> **After a defect is fixed, which prompt would have prevented it — and did you change that
> prompt, or only the code?** Answering "the fix is obvious now, anyone would catch it" is the
> wrong answer: the next author arrives with less context than you have at this moment, which is
> the only moment the rule is cheap to write. **If no existing rule would have caught it, add or
> sharpen one where its consumer already loads it; if one exists and did not fire, the defect is
> in its phrasing or its placement, and that is what to repair.**

Two constraints keep this from becoming prose inflation, and both come from rules already here:

- **Extend before you mint** (`gate:design-principles-gdp-10-parsimony`). Ask whether a more
  general existing rule already covers the case. A new numbered principle for something a
  corollary can carry is the ceremony that clause exists to refuse.
- **Ship the counterexample with the rule** (row 4 above, applied to prose). A normative sentence
  without the dated case that generated it erodes at the first rewrite: the next editor sees an
  assertion with no cost attached and trims it. The anchor is what makes the rule survive.

This is deliberately blame-free and forward-facing. The question is never who wrote the test or the
component that broke — it is which instruction, had it existed, would have made the class
unwritable. Empirical anchor, 2026-08-06: three CI-only failures across three suites turned out to
be one class (a test inheriting ambient host state rather than declaring it), and the durable
output of that day was not the three fixes but the mandate and the two design clauses that make the
class visible at authoring time.

## `provenance:a-count-without-a-sender-is-not-attributable` — name who wrote the record before it becomes evidence (STANDING)

A count extracted from a SHARED log or ledger is a claim about the SENDER of each record, not only
about the event it names. Before a count feeds a ranking, a defect row, or a dispatch decision, the
question is not "how many?" but "who wrote each one, and is that population the one the claim is
about?" A number is not evidence until that second question has an answer.

MEASURED 2026-08-03: an audit counted 225 formatting-check block records from a shared PreToolUse
log and concluded a re-fire pattern existed across four step-ids, ranking a detector as the top fix
candidate. The count was real; the attribution was not checked. 224 of the 225 records were written by
the project's OWN acceptance suite — two test files pointed the tool at the real repo instead of an
isolated one, defeating an isolation fixture, and every test run deposited identical records into the
SAME shared log a real dispatch would write to. The suite and the product were indistinguishable in
the log, because the log carries no field that reliably separates them (`run_context`/`subagent_type`
were checked and do not discriminate). Cost of the unattributed count: a fix was dispatched against a
defect that did not exist, and a downstream ranking (which mechanism to fix first) was wrong until the
attribution was checked.

**The check that actually discriminates, when the log has no reliable sender field**: cluster by
BURST, not by a fixed count threshold. Machine-generated repetition (a test loop, a retry storm) fires
at machine cadence — sub-second gaps, tight clusters of near-identical size — while independent
real-world events do not share that rhythm. Measured: 263 records clustered into 102 bursts by a
<500ms gap boundary; bursts of 5-7 records were, without exception, the SAME reason repeated at a
median 30ms internal gap, concentrated on a handful of calendar days — the signature of a test loop,
not of an agent retrying a blocked dispatch. The singletons left over after excluding bursts were the
population the original claim should have been about.

Corollary — **a shared substrate that a test suite writes into by design, and mitigates only by
SERIALIZING (never isolating), keeps producing this trap indefinitely.** If ~N test suites are
documented as deliberately pointing a tool at the real, shared state (not a fixture copy) because
isolating them was harder than serializing their access, then every count taken from that shared
state carries an unknown contamination fraction FOREVER, not just once — the fix is not re-deriving
the attribution each time a number is needed, it is closing the shared-write
path itself. Keep test writes isolated from production observations.
