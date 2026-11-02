---
name: nw-solution-architect-formal-verification
description: "PROCEDURE — formally verify every design's algebraic claims with need-selected checkers and explicit host-relayed installation or human waiver."
user-invocable: false
---

# Formal DESIGN Verification

**Kind**: PROCEDURE. **Job**: formally verify design claims with their scope.
**Trigger**: every design defaults to algebraic modeling with formal verification.
Select claims and checkers by need: local totality, inhabitation, canonicalization
and preservation proofs; state-transition safety/refinement/reachability,
liveness/fairness/concurrency/recovery; and modelable non-functional observations
such as deadlines, queues, isolation, availability or recovery time.
Record which checker covers each claim and why; routine/local designs are not exempt.

Completion requires an executed selected checker on the model/proof plus
property-specific falsification evidence. An available Quint installation
must be used, not replaced by a Python enumerator, even for a small finite
state space. Model authoring or syntax difficulty is not tool unavailability:
repair the model and run it, using the execution host when required by your
capabilities. If execution cannot be completed, leave the selected formal
claim `INDETERMINATE`, not PASS on substitute evidence.

## Deterministic sequence

1. **Classify** — select Agda for proofs; Quint for state models; TLA+/TLC
   when Quint is insufficient for the actual claim (for example required
   liveness under fairness). Select both/all when one checker cannot cover
   the claim. Record the claim-to-checker mapping and reasons in `decisions`.
   Preserve useful existing TLA+ models. Decompose mixed obligations; finite
   exploration does not make a requested liveness guarantee irrelevant.
2. **Probe tools** — detect the host platform and use its native execution,
   environment and directory-observation capabilities. For selected Agda,
   execute `agda --version`; for Quint, execute `quint --version` (or its
   configured local binary) and `java -version`. Observe `QUINT_HOME` through
   the host's environment API, then inspect the resolved installation/backend
   directory through its native file capability. If the variable is absent,
   resolve the observed user's home and Quint's documented default for that
   installation; do not assume shell home expansion or a glob command.
   Retain the concrete configured/resolved location and observed selected
   backend identity; PATH alone does not locate Quint's backend. A missing
   backend may be downloaded by verification (see step 5). For direct TLA+,
   execute `java -version` and locate the actual `tla2tools.jar`.
   Configuration is not availability evidence. If the necessary observation
   capability is unavailable, ask the host for that bounded observation or
   retain the affected capability limitation; do not assume a platform,
   package manager or shell behavior.
3. **Run** — execute available Agda. For Quint, first execute `quint typecheck`,
   then `quint run` for exploration (no backend) and `quint verify` with the
   selected backend for model checking. Use the serial bound-growth and
   liveness protocols below. Retain complete external model/proof files and
   driven execution evidence under Delivery and evidence locators.
   A passing simulation is not a completed formal
   verification. Both `quint verify` backends first start a local Apalache
   server, and TLC itself opens a local socket; when the sandbox refuses it,
   record that failure and verify the same `.qnt` without a server:
   execute `quint compile --target json M.qnt` and capture its emitted JSON
   through the host's output/file capability into `M.qnt.json` (Apalache reads
   Quint input only from a file named `*.qnt.json`), then
   `apalache-mc check --init=… --next=… --inv=… --length=…` for a safety claim
   on it with the same names and bound, using `apalache-mc` from
   `apalache-dist-<version>/apalache/bin` in the probed directory.
   A safety fallback does not discharge temporal claims. Use TLC for selected
   liveness and fairness; experimental Apalache temporal support and an
   interactive confirmation are not a completed liveness check.
   For TLA, execute declared temporal properties with necessary fairness;
   create/reuse a `.tla` model and `.cfg`
   configuration and actually pass both files to TLC. Record literal argv, exit
   status and result in the driven evidence store. Deliver every selected
   model/proof as an external source file cited by `Model.source: {path, sha256}`;
   never embed its bytes in constructor input. A disposable checker copy is
   not the delivered model. Run checkers on an outside-repository copy so
   generated outputs (`.agdai`, `_build`, `_apalache-out`) stay out.
   Create probe files only where your capability surface grants it; otherwise give your host
   their exact text, path and checker argv to write and execute, and record the
   returned receipts. Label hand enumeration, scripts and prose separately;
   none replaces the selected checker. Intended commands, missing configuration
   or an unexecuted checker leave the selected proof `INDETERMINATE`.
   **Discriminate the selected obligations.** For each property claimed as
   verified, link it to the behavior/observation it names and run the same check
   on a targeted behavioral mutant, not a changed property definition or flag.
   Before reporting completion, does each selected property have matching
   actual checker evidence and a behavioral-mutant counterexample/rejection,
   rather than an intended command, remembered result or tool/setup error?
   If not, execute the missing matching check within authorized capabilities;
   if it remains unexecuted or lacks discrimination, retain that limitation
   and withhold the verified claim. For Quint safety mutants,
   first run `quint run --invariant`; a real counterexample is a valid kill,
   labelled simulation, not exhaustive verification. Escalate to `quint verify`
   only when simulation finds none. Agda retains a rejected mutant module or
   checked refutation. A tool/setup error or timeout is not a kill.
   For a conjunction, one mutant violating one clause does not discriminate
   the others: retain each selected clause's relevant counterexample, reusing
   a mutant only when its trace actually violates that clause. Keep this check
   proportionate to the
   selected obligations, not every helper lemma. Missing mutant discrimination
   is insufficient falsification evidence: mark that claim unverified and
   investigate its observation or strengthen the model when warranted. Failure
   to find a mutant is not a mathematical proof of vacuity; establish vacuity
   from the property's semantics before calling it vacuous.
4. **Refine** — name model atoms, runtime symbols, exclusions and refinement.
   For `RED_TO_GREEN`, a runtime implementation is not required: record the
   mapping/refinement obligation and declared limits. A verified design model
   with complete mapping may support DESIGN coverage, but never runtime
   coverage. Gate: absent mapping is unrefined model-only evidence, never
   COVERED. T5 models declared progress/liveness only; T6 names real guarantor,
   monitor and failure consequence; T7 names exact code reference and
   mechanism/protocol atomicity, or `QUESTION/NEEDS_INPUT`.
5. **Offer installation or human waiver** — a missing needed checker stops
   that proof, not the algebraic modeling requirement. Report indeterminate
   assurance with a diagnostic naming the missing tools,
   affected claims, observed platform, and two human choices: install the tools
   with exact platform-specific commands, or explicitly waive that verification.
   As a consulted lens, relay the same plain diagnostic to the design owner; the host relays it to the human.
   Do not ask the human yourself, auto-download a backend, install without
   authorization, silently downgrade to native tests, claim PASS or fake a run.
   Only a recorded human waiver permits continuation without that proof.
   Keep the explicit waiver evidence external; reference only its current
   affected claim and reason through FactRefs. The proof stays `INDETERMINATE`.
   A refusal to install is not itself a waiver. An unknown platform/package
   manager requires a bounded host observation, not an invented install command.
   Provide only the dependencies actually needed by the selected claims.
   Examples to adapt after observing the platform and available tools:

   | Needed tool | Installation offer (host relays; never execute without consent) |
   |---|---|
   | Quint with Node.js/npm available | `npm install -g @informalsystems/quint` |
   | Java/Agda on observed Arch Linux | `sudo pacman -S jre-openjdk agda` (select only missing packages) |
   | Direct TLC with Java available | `curl -fL --output <outside-repo>/tla2tools.jar https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar` |

   Keep equations, observations and vacuity checks while waiting for the host's
   decision; missing tools do not authorize an accepted proof-less design.
   State the limitation and any representation gap in the design findings.
   Preserve the real limitation as indeterminate rather than inventing a proof.

## Serial execution and bound growth

Run checkers one at a time: shared backend resources can collide. Use the
execution host's portable process deadline, not an assumed shell `timeout`.
Budget each verification/TLC run at 180 seconds unless current authority states
a different explicit budget; retain the limit with the result.
Start at the smallest instance that reaches the seam: two processes and the
fewest relevant steps for a concurrent claim, or the corresponding minimal
local instance. Increase only after the previous run finishes within budget:
two processes -> three -> failures -> liveness. Record completed bounds and
where growth stops. A timed-out bound is `INDETERMINATE`; do not repeat it
unchanged. Smaller focused slices may resolve different claims, never stand in
for the timed-out property at its promised scope.

## Liveness and fairness

Use a finite TLC slice with the state needed by the temporal property and its
actions; remove ghost histories and unbounded counters only when the projection
preserves those behaviors. State the projection limits. Retain its complete
text just as for the safety model.

Express assumed fairness as a temporal formula, for example
`weakFair(action, vars)` or `strongFair(action, vars)`, with its actual action
and variables. Explain whose scheduling/progress obligation it assumes.
For a Quint model, the native form is:

```text
quint verify MODEL.qnt --init=init --step=step --temporal=PROPERTY --backend tlc
```

Keep distinct executed runs and receipts for:

| Run | Required observation |
|---|---|
| Progress property without fairness | Counterexample showing the admitted stuttering/do-nothing behavior |
| Property under declared fairness | Passing check on that finite scope |
| Mutant removing progress or release, under the same fairness | Counterexample refuting that progress guarantee |

Keep the raw traces, not only summaries. If the no-fairness claim already holds,
explain the model's actual progress guarantee rather than invent stuttering.
If the declared protocol has no truthful matching evidence, its liveness DESIGN
axis stays `BLOCKED`; retain runtime and proof results independently.
Finite-state checking proves neither unbounded runtime scheduling nor elapsed
time; name those remaining obligations and owners.

## Delivery and evidence locators

Supply claim descriptions, complete model/proof source paths, properties, atoms,
mutants and their relationships. Distinguish shared assurance from slice-specific
obligations. Keep complete model/proof files at intended repository-relative paths.
Retain one receipt file per native execution beside the model: checker and
version, literal argv, exit status, stdout, stderr and model sha256.
Cite source and receipt paths; locators alone establish no execution.
Never invent a receipt command, inline model field or separate run store.

| Evidence | Required external content |
|---|---|
| Model/proof and temporal slice | Complete unedited file with line breaks; language, sha256 and committed source path |
| Checker run | Actual argv, tool version, backend/configuration, properties, bounds or seed, exit, result and raw outputs/traces |
| Mutant | Exact changed behavior, model identity, property it falsifies and its counterexample/rejection receipt |
| Refinement | Each action/step's file, symbol and mechanism making it atomic, or the real seam splitting it; unmapped steps explicitly model-only |

A hash, scratch file, intended command or successful version probe is not model
delivery or verification. Claim property coverage only for checks the actual
run exercised; an aggregate green result does not supply missing law receipts.
Keep observed process facts separate from declared checks and interpretation.
Replay evidence retains its original revision; it is not a newly observed run.
When no callable capability can execute or persist the required evidence,
return that bounded limitation to the host and leave the claim `INDETERMINATE`.

Downstream roles need current design facts and evidence locators. A generated
prompt or brief does not check a model or substitute for native execution.
Missing model context, an unresolved claim or a cited-but-unreadable receipt
is not a passing formal check.


## Non-functional requirements and human review

Name the actor, observation, operating conditions, units and threshold before
modeling a non-functional requirement. Use explicit time, resource and fault
assumptions: state-transition count is not elapsed time. Separate real failure
from detected failure, and stated capacity from measured throughput. Model
checking can establish a property of those assumptions; actual latency,
throughput, recovery and availability still need their relevant runtime tests.
Do not claim a production percentile or service level from model exploration.

Reuse the PO's behavioral core where available, then make architectural
refinement and preservation obligations explicit. Render relevant traces into
domain-language scenarios for human review using `nw-po-scenario-exploration`;
the human need not read Quint or TLA+. Keep raw traces and model identity.

## Composition

- `nw-algebraic-design-protocol` — observations, equality and public terms.
- `nw-certainty-by-construction` — local construction boundary.
- `nw-formal-verification-tlaplus` — TLA+/TLC modeling heuristics.

## Verification

Do these items have current model/artifact and executed-check evidence where
required, rather than presence, declarations or recollection? If not, retain
each affected limitation in the supported semantic carrier and withhold only
the unsupported claim; obtain missing authorized evidence where possible.

- [ ] Tool availability was executed, not asserted.
- [ ] An available selected checker ran on the actual model/proof (own or host
  receipt); substitute evidence is labelled separately.
- [ ] The selected tool and property match local or state-transition trigger.
- [ ] A new state model uses Quint, or the authority records why direct TLA+ is required.
- [ ] Probe and any installation offer match the actual host platform.
- [ ] The authority names mapping, exclusions, mapping/refinement obligation
  and declared limits; it never calls a model result runtime coverage.
- [ ] A Quint verification records `.qnt`, backend/configuration, properties,
  bounds, literal argv, exit status and result; simulation is labelled separately.
- [ ] A TLA run records `.tla`, `.cfg`, literal TLC argv, exit status and result.
- [ ] Non-functional model assumptions and required runtime measurements are explicit.
- [ ] A missing checker has an indeterminate assessment naming tools, affected claims,
  platform-specific installation commands and a host-relayed human waiver option.
- [ ] Any continuation without a required proof has a recorded human waiver;
  affected claims retain `INDETERMINATE` and the waiver reason, never PASS.

Reference: https://quint.sh/docs/quint#command-verify
