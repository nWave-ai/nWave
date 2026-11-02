---
name: nw-nwdes
description: nwdes routes and verbs for host-led delivery of a Request.
user-invocable: false
---


# nwdes

## Route

- The root writes product facts and promises itself.
- Every new product slice cites existing Request promises with repeatable --promise P<n>; add a justified Request promise with product promise add, or split unrelated outcomes into a separate nwdes feature new. Product close requires every slice linked and every Request promise covered; independent slices and every work size remain valid.
- Ask the product owner only on ambiguity or a genuine scope or trade-off question.
- When the Request already states the outcome, no product owner turn or Quint model is required as a product prerequisite.
- There is no separate oracle review beyond the independent approval of each public oracle before craft, an artifact-quality check of that oracle alone; no per-slice charter.
- Prose-only change: a change whose every target is a Markdown or template prose asset is recorded as a prose-only slice: `nwdes slice set` with its targets and promise references and none of `--oracle`, `--stimulus`, `--expected`, `--falsifier`, `--command` or `--support`. nwdes records its acceptance as `NotTested` with reason `prose, verified by EXAMINE`; no acceptance designer is run for it, and EXAMINE plus the whole-candidate review verify it.
- Never couple prose to tests: never write a test that pins the wording of a prose target. Exact public text is pinned only for a machine contract of a shipped surface (schema, table grammar, CLI output format, parse rule), per `nw-test-design-mandates-composition-contract`.
- Run a separate design review only when a shared decision or ADR changes, as nwdes delta computes; otherwise no separate design review is needed.
- Review scopes: Embedded refinement review of a GREEN slice is optional feedback that reduces risk; build it with --diff from the slice's base commit and --slice S<n>, and record it with --subject slice --slice S<n>. The one required review is a fresh independent whole-candidate review after all slices are built, recorded with --subject candidate; it never consults embedded review records, and an embedded approval never counts as it. One source-blind EXAMINE judges the complete Feature, never an individual slice; the examiner never receives producer discussions or embedded findings and returns its verdicts once on the assembled candidate revision before integrate. The independent approval of each oracle before craft stays.
- Smaller slices: Use one slice by default when one behaviour suffices; each slice delivers one observable behaviour a reviewer judges in one short pass. A feature has at most 5 slices. The first slice is the one walking skeleton and every later slice extends it with explicit dependencies. The Request keeps its whole value and shared design. A technical layer or mocked interaction is not a slice.
- Start a slice once the slices it declares as dependencies are GREEN; independent slices may proceed in parallel. Keep every test file collectable.
- Code facts: read nw-code-analysis-port and use code-fact first for callers, readers, file atoms and never-wired paths; use Read or Grep only where it cannot answer, including indeterminate, and identify fallback facts.
- Jev: use nw-typesafe-system-one only when authorized and available, after mechanical code facts; its advice is not a verdict. Otherwise record typesafe: unavailable and continue locally.
- If an installed role cannot run, stop with its cause. Only human authorization permits the host's default agent to run the exact generated role prompt and verb contract instead; report that substitution, never do the role's work yourself.
- Review evidence: Each verification has one owner. Each review's responsible reviewer owns selection and sufficiency of the touched-file selected tests for its declared phase scope; the final reviewer alone owns the assembled whole-candidate scope. It reuses a complete applicable native result (host, CI or the normal commit hook) whose source, test, argv and runtime inputs are unchanged, citing its original operator and run; it executes only missing or affected checks, once, and records argv, exit status, stdout and stderr of each run it executes with nwdes review observation add. Reuse never waives a check. nwdes never selects or runs tests, and the root never runs a duplicate readiness round. Scope: oracle/support files since slice base for oracle review; slice files since slice base for embedded review; assembled candidate files since feature base for final review; design files named in root-context for design review only when a shared decision or ADR changes. Missing touched-file observations, host observations not run, or failing selected tests are findings. NotTested is not a waiver: absence of pytest does not remove an assigned observation. Immutable evidence named by the packet is readable by the reviewer before assessment; sealed examiner or private producer evidence stays closed.
- Oracle and RED: Before craft, require a public, constructible oracle with its observed semantic RED for the agreed missing behavior, not completed implementation GREEN or future live delivery. Tested identifies executable coverage, not a claim that execution passed. Root dispatches the crafter once that oracle is approved and its RED is recorded.
- Findings and rebuild: Only defects invalidating the current phase block its work. Accepted review may retain non-blocking findings with their owner, remedy and affected phase; unresolved promised outcomes still block completion. The root rebuilds only the bundles nwdes delta lists AFFECTED, without a full handoff pass.
REJECT round: On a rejected close, nwdes prints every finding owner's role and its read command together. Each owner reads exactly its own findings with nwdes review findings --owner O. Owners fix a demonstrated defect directly: they resolve routine questions with the reviewer through native peer messaging when the host provides it, and retain the existing root route only where messaging is genuinely absent (an unknown or failed capability probe does not establish absence). Each owner edits only its own artifact with its own verbs and records only its delta with open --from-current. A revised oracle needs independent re-approval, an artifact-quality check of that oracle alone with its observed semantic RED, before the crafter aligns production; reassess only the affected obligations. The reviewer reassesses only the affected delta and reopens its own record with open --from-current, removing only resolved findings. A refuted fix or an owner disagreement stays open and escalates to the host; never record it closed.
- Role commits: The orchestrator decides when and how to commit, normally one plain `git commit` of a GREEN slice with hooks on. `nwdes commit --role ROLE` stays an optional verb that commits the role's changed owned files, including its run record; an explicit `--path` naming another role's file commits it when this role holds a close receipt, and an unowned path is refused. nwdes imposes no commit after a close and none before craft. Git author identity and hooks remain enabled; nwdes never passes --no-verify. Plain Git commits remain available to humans and outside nwdes deliveries.
- Lanes are optional in an isolated checkout or for a single bugfix. Without a lane, the delivery runs in the current clean checkout and the orchestrator commits the GREEN candidate; skip lane open, compose and integrate, and review and examine that same committed candidate. No lane-free flag is needed.

## Reply transport

Each role receives one complete inline bundle from nwdes prompt, ending with that role's generated verb reference. Jev consent is authorized by default: with no `--jev` flag and no `"jev"` declared in the repository or global configuration (`~/.nwave/config.json`), the bundle states `jev: authorized`. Refuse with `--jev unauthorized` on the call or `"jev": "unauthorized"` in a configuration tier; the flag wins, then the repository tier, then the global tier. Jev acts only when `TYPESAFE_API_KEY` is set; nwdes never reads, logs or writes that key. The bundle prints the resolved value. Roles record values through their verbs; nwdes builds ids, form and serialization. No role writes JSON.

Every recording role, including the product owner and examiner, uses its kind's nwdes CLI verbs through Bash to record values and closes with outcome and diagnostic. Run every nwdes command from the top level of the checkout; roots default to cwd and the repository root, and lane verbs resolve the main worktree. The first add, set or remove creates the scoped draft; open --from-current only revises authority already published, never as the first call of a first recording. Retain unchanged rows and remove replaced rows before adding; reference existing ids only. Close with no draft validates empty values.

The root builds prompts and consumes the host's attributed evidence for the slice's declared commands; it executes only host-owned commands, never repeats a declared command, and never copies a reply into apply or writes a handoff by hand. On refusal, return the complete diagnostic to its owner, fulfill a named prerequisite if authorized, and rebuild the same role/task bundle when inputs change.

Crafters use craft file add and command add, then craft close with accepted or rejected and an unblocking owner on rejection. Inside Git every crafter supplies its own explicit --role to craft close; the receipt names that actor, never a default or an inference from the paradigm, and the run record stays unchanged. Reviewers gather their own evidence with review observation add, record review finding add and review close; stamps are supplied by nwdes, never typed by the reviewer. nwdes writes these records under the feature's runs directory, not into the handoff. Local GREEN, independent review and EXAMINE remain separate obligations.

The orchestrator decides when and how to commit; nwdes imposes no commit after a close and none before craft. Commit with one plain `git commit` of a GREEN slice with hooks on, or with the optional `nwdes commit --role ROLE` described above. Several authority closes may stand uncommitted at once. Git author identity and hooks remain enabled; nwdes never passes --no-verify. Plain Git commits remain available to humans and outside nwdes deliveries.

The examiner's packet carries public promises, slice observations and public oracles, the Feature charter, fixed expectations and a public-only examination workspace, never source code, producer RED/GREEN, diffs, reviews or private design evidence. The examiner gathers its own observations with nwdes examine read and nwdes examine probe, and records each through its generated recording verbs before citing it. The host supplies no observations or root context for examine. The examiner keeps plain Bash; nwdes guarantees its packet, workspace and read/probe boundaries, not confinement of the examiner process. Product owners likewise work from the user's point of view. Both record values through the same CLI as every other role. The optional charter API is not a route step.

There is one optional charter per complete Feature, never per slice. One source-blind EXAMINE covers the complete Feature, never per slice.

Examine findings and parity: a rework that repairs an examine finding adds that finding as an oracle test, observed RED before the repair and GREEN after it, added before or with the rework; the acceptance and craft bundles of a reworked slice state this rule. If the Request promises parity with a reference behaviour, its oracle contains a differential test (the same inputs run against the reference and the new behaviour, with equal answers), and EXAMINE does not re-do parity. When no executable reference exists, the Request says so, and the host dispatch states a raised examine budget for that Request; the recipe prints the one constant 5 as its default.

No prompt recipe or packet accepts --observation or --observation-file: SelfGatheredEvidence refuses these retired flags before reading files or printing a bundle. Reviewers record literal UTF-8 observations with nwdes review observation add --text or --text-file; examine likewise records its own observations.

## Full route

1. Choose whether to use a lane.

   For a feature worked from the main worktree on the trunk branch, open a lane first. In an already isolated checkout, the delivery runs in the current clean checkout without a lane; skip the lane commands below. Its lane configuration names the intended existing trunk branch; main is only an example, not a default. Keep existing settings and merge the lane setting into .nwave/config.json. Prepare host-only output files outside the worktree.

   ```sh
   ROOT=$PWD
   LANE="$ROOT/lanes/search"
   OUT="$HOME/.cache/nwdes/search"
   mkdir -p "$OUT"
   nwdes lane open --feature search
   ```

2. Create the feature inside the lane.

   Enter the lane's top level before creating the feature. Keep the request verbatim and choose its value and size; size never chooses the route. H below uses the default destination; use the handoff path printed by this command if configuration overrides it. Provide the lane's declared program files or an invoking PATH on which they resolve.

   ```sh
   cd "$LANE"
   nwdes feature new --feature search --request Search --size M --value Find
   H="$LANE/docs/feature/search/handoff.json"
   ```

3. Write root product facts and promises.

   The root records product facts directly with typed verbs from the Request; never writes product.json. Keep one slice when one behaviour suffices. Cite the promise IDs the draft will publish: retained published words keep their IDs, new promises use the next published counter, and first-draft promises are numbered after removals. Close refuses missing or unknown slice links and uncovered Request promises. GDP-9: Does every slice contribute to this one value, or did you bundle unrelated outcomes? Do not answer yes by default. Split unrelated outcomes into a separate nwdes feature new.

   ```sh
   nwdes product promise add --feature search --kind Outcome --text "The search result is returned"
   nwdes product slice add --feature search --observation Find --promise P1
   nwdes product close --feature search --outcome accepted --diagnostic "Recorded Request facts"
   ```

4. Design the feature.

   Retain the previous handoff, then invoke the architect with the complete bundle. The architect records values with nwdes design verbs and nwdes design close. Run a separate design review only when nwdes delta shows a changed shared decision or ADR.

   ```sh
   cp "$H" "$OUT/before-design.json"
   nwdes prompt --role nw-solution-architect --handoff "$H"
   ```

   ```sh
   nwdes delta --previous "$OUT/before-design.json" --new "$H"
   ```

5. Fix examiner expectations once for the feature.

   Build the expectations prompt from public product facts before any oracle authoring. The examiner records rows with nwdes expectations row add and nwdes expectations close, then leaves its published files for the orchestrator to commit. E1 stands for actual fixed expectation ids; cover them all. Revise only through nwdes expectations open --from-current and nwdes expectations close --revise, never to fit implementation.

   ```sh
   nwdes prompt --role nw-user-examiner --task expectations --handoff "$H"
   ```

6. Author and record the slice's oracle.

   Build the acceptance-designer bundle for S1 with its promises and public oracle. The acceptance designer writes the oracle and named supports, not production, records coverage with nwdes acceptance row add and nwdes acceptance close, and leaves its files for the orchestrator to commit when it chooses. The oracle then receives independent acceptance-oracle approval before craft begins; that approval is current and not a separate oracle review phase. Repeat this per-slice stage for each designed slice, before the declared commands, crafter, GREEN, whole-candidate review and examine.

   For each test, record with --still-passes-if the nearest plausible wrong behaviour it would still accept, and tighten the test when that behaviour violates its promise.

   Author the oracle while the focused baseline is gathered, reusing pertinent known observations. Do not hold authoring behind a broad readiness pass. A constructible oracle with semantic missing-behavior RED can be approved before implementation GREEN or future native delivery; those remain completion obligations.

   ```sh
   nwdes prompt --role nw-acceptance-designer --handoff "$H" --slice S1
   ```

7. Craft one slice and observe its declared commands.

   Use a real observed RED baseline for declared commands: run them if no earlier trusted observation supplies it, never invent it or rerun a reported failure merely to confirm it. If DESIGN declares prefactoring, preserve before-move and after-move-before-behavior evidence before changing behaviour. Invoke the functional crafter when design.paradigm is functional, otherwise the software crafter, with the generated bundle. The crafter changes only owned targets, never the oracle, and records files, commands and outcome with craft verbs. The host observes each slice's RED and GREEN for its declared commands; the root does not repeat them. An embedded refinement review of the slice is optional feedback; when run, resolve its findings through the REJECT round before the next slice.

   REJECT round: On a rejected close, nwdes prints every finding owner's role and its read command together. Each owner reads exactly its own findings with nwdes review findings --owner O. Owners fix a demonstrated defect directly: they resolve routine questions with the reviewer through native peer messaging when the host provides it, and retain the existing root route only where messaging is genuinely absent (an unknown or failed capability probe does not establish absence). Each owner edits only its own artifact with its own verbs and records only its delta with open --from-current. A revised oracle needs independent re-approval, an artifact-quality check of that oracle alone with its observed semantic RED, before the crafter aligns production; reassess only the affected obligations. The reviewer reassesses only the affected delta and reopens its own record with open --from-current, removing only resolved findings. A refuted fix or an owner disagreement stays open and escalates to the host; never record it closed.

   ```sh
   nwdes prompt --role nw-functional-software-crafter --handoff "$H" --slice S1
   ```

   Optionally, before an embedded refinement review, the orchestrator commits the reviewed slice when it chooses. Capture its complete diff from its base commit in $OUT/slice.diff. The reviewer gathers its own native run evidence:

   ```sh
   nwdes prompt --role nw-software-crafter-reviewer --handoff "$H" --slice S1 --diff "$OUT/slice.diff" --commit HEAD
   ```

   The embedded reviewer, not the root, records its own outcome through its generated verbs, for example:

   ```sh
   nwdes review observation add --feature search --subject slice --slice S1 --text-file "$OUT/reviewer-run.txt"
   nwdes review close --feature search --subject slice --slice S1 --outcome accepted --diagnostic "Embedded findings confirmed"
   ```

8. Run one fresh independent final whole-candidate review.

   After all slices are GREEN, the orchestrator commits them when it chooses and the root composes the candidate at trunk. Retain printed EXPECTED and CANDIDATE identities; verify again if composition changed it. Capture its whole diff from the feature base, including approved oracles and supports, in $OUT/candidate.diff. The final reviewer owns selection and sufficiency of its tests on that clean committed candidate, under the verification rule below. Route findings to their owner.

   Verification has one owner per check. The final reviewer owns selection and sufficiency of the touched-file selected tests over actual tracked and untracked files since the feature base. It reuses a complete applicable native result (host, CI or the normal commit hook) whose source, test, argv and runtime inputs are unchanged, citing its original operator and run; it executes only missing or affected checks, once, and records each run it executes with nwdes review observation add. nwdes never selects or runs tests. Reuse never waives a check. Host-owned live native observations are recorded separately as host evidence. A documentation, authority or review-record commit alone is not a rerun trigger. An absent selector or an empty selection is a result to record, not a waiver. Never pick tests from memory. Missing touched-file observations, host observations not run, or failing selected tests are findings.

   ```sh
   nwdes lane compose --feature search
   nwdes prompt --role nw-software-crafter-reviewer --handoff "$H" --diff "$OUT/candidate.diff" --commit HEAD
   ```

   The final reviewer, not the root, records its own outcome through its generated verbs, for example:

   ```sh
   nwdes review observation add --feature search --subject candidate --text-file "$OUT/reviewer-run.txt"
   nwdes review close --feature search --subject candidate --outcome accepted --diagnostic "Whole candidate reviewed"
   ```

9. Obtain the examiner verdicts.

   After candidate review, build the examiner's complete bundle without host observations or root context. It names a public-only workspace of committed public documents and scratch, plus nwdes examine read and nwdes examine probe. The examiner gathers its own observations there, records each through the generated examination recording verbs before citing it, judges every fixed expectation from the user's point of view, and closes. Supply public inputs, never review, diff or producer verification.

   ```sh
   nwdes prompt --role nw-user-examiner --task examine --handoff "$H"
   ```

10. Integrate the accepted candidate.

   Use the unchanged EXPECTED and CANDIDATE printed by compose, after verification, accepted candidate review and examiner verdicts for that candidate. If trunk or candidate changes, reconcile and reassess the affected evidence before retrying; do not reuse a verdict for another candidate. Classify remaining lane files before integration: lane integrate merges and removes the lane without force. Rerun the same command after an effect failure.

   ```sh
   nwdes lane integrate --feature search --expected "$EXPECTED" --candidate "$CANDIDATE"
   ```

## M and bugfix route

For a single understood defect, use this route; the root supplies the product and design facts itself.

1. Work in the current clean checkout without a lane.

   Run and commit in place; keep evidence outside the checkout.

   ```sh
   LANE=$PWD
   OUT="$HOME/.cache/nwdes/search"
   mkdir -p "$OUT"
   ```

2. Create the feature inside the lane.

   Enter the lane's top level before creating the feature. Keep the request verbatim and choose its value and size; size never chooses the route. H below uses the default destination; use the handoff path printed by this command if configuration overrides it. Provide the lane's declared program files or an invoking PATH on which they resolve.

   ```sh
   cd "$LANE"
   nwdes feature new --feature search --request Search --size M --value Find
   H="$LANE/docs/feature/search/handoff.json"
   ```

3. Write the bugfix slice and its promise.

   The root writes the slice's observation, public stimulus, expected result, falsifier, promise, targets and a verification command that resolves in the writer's environment. Preserve the real defect and promise, not a workaround.

   ```sh
   nwdes slice set --feature search --observation Find --paradigm functional --oracle tests/search.py --stimulus Search --expected Found --falsifier Missing --command 'python tests/search.py' --promise 'The search result is returned' --extend src/search.py
   ```

4. Fix examiner expectations once for the feature.

   Build the expectations prompt from public product facts before any oracle authoring. The examiner records rows with nwdes expectations row add and nwdes expectations close, then leaves its published files for the orchestrator to commit. E1 stands for actual fixed expectation ids; cover them all. Revise only through nwdes expectations open --from-current and nwdes expectations close --revise, never to fit implementation.

   ```sh
   nwdes prompt --role nw-user-examiner --task expectations --handoff "$H"
   ```

5. Author and record the slice's oracle.

   Build the acceptance-designer bundle for S1 with its promises and public oracle. The acceptance designer writes the oracle and named supports, not production, records coverage with nwdes acceptance row add and nwdes acceptance close, and leaves its files for the orchestrator to commit when it chooses. The oracle then receives independent acceptance-oracle approval before craft begins; that approval is current and not a separate oracle review phase. Repeat this per-slice stage for each designed slice, before the declared commands, crafter, GREEN, whole-candidate review and examine.

   For each test, record with --still-passes-if the nearest plausible wrong behaviour it would still accept, and tighten the test when that behaviour violates its promise.

   Author the oracle while the focused baseline is gathered, reusing pertinent known observations. Do not hold authoring behind a broad readiness pass. A constructible oracle with semantic missing-behavior RED can be approved before implementation GREEN or future native delivery; those remain completion obligations.

   ```sh
   nwdes prompt --role nw-acceptance-designer --handoff "$H" --slice S1
   ```

6. Observe the bug reproduction RED.

   Use a reported pre-fix failing observation when it supplies the declared evidence; otherwise run the declared verification on the original pre-fix revision. Keep the tree collectable; a setup or collection error is not evidence of the requested defect.

7. Craft one slice and observe its declared commands.

   Use a real observed RED baseline for declared commands: run them if no earlier trusted observation supplies it, never invent it or rerun a reported failure merely to confirm it. If DESIGN declares prefactoring, preserve before-move and after-move-before-behavior evidence before changing behaviour. Invoke the functional crafter when design.paradigm is functional, otherwise the software crafter, with the generated bundle. The crafter changes only owned targets, never the oracle, and records files, commands and outcome with craft verbs. The host observes each slice's RED and GREEN for its declared commands; the root does not repeat them. An embedded refinement review of the slice is optional feedback; when run, resolve its findings through the REJECT round before the next slice.

   REJECT round: On a rejected close, nwdes prints every finding owner's role and its read command together. Each owner reads exactly its own findings with nwdes review findings --owner O. Owners fix a demonstrated defect directly: they resolve routine questions with the reviewer through native peer messaging when the host provides it, and retain the existing root route only where messaging is genuinely absent (an unknown or failed capability probe does not establish absence). Each owner edits only its own artifact with its own verbs and records only its delta with open --from-current. A revised oracle needs independent re-approval, an artifact-quality check of that oracle alone with its observed semantic RED, before the crafter aligns production; reassess only the affected obligations. The reviewer reassesses only the affected delta and reopens its own record with open --from-current, removing only resolved findings. A refuted fix or an owner disagreement stays open and escalates to the host; never record it closed.

   ```sh
   nwdes prompt --role nw-functional-software-crafter --handoff "$H" --slice S1
   ```

   Optionally, before an embedded refinement review, the orchestrator commits the reviewed slice when it chooses. Capture its complete diff from its base commit in $OUT/slice.diff. The reviewer gathers its own native run evidence:

   ```sh
   nwdes prompt --role nw-software-crafter-reviewer --handoff "$H" --slice S1 --diff "$OUT/slice.diff" --commit HEAD
   ```

   The embedded reviewer, not the root, records its own outcome through its generated verbs, for example:

   ```sh
   nwdes review observation add --feature search --subject slice --slice S1 --text-file "$OUT/reviewer-run.txt"
   nwdes review close --feature search --subject slice --slice S1 --outcome accepted --diagnostic "Embedded findings confirmed"
   ```

8. Run one fresh independent final whole-candidate review.

   Commit deliberately and capture the whole candidate diff, including approved oracles and supports, in $OUT/candidate.diff. The final reviewer owns selection and sufficiency of its tests on that clean committed candidate, under the verification rule below.

   Verification has one owner per check. The final reviewer owns selection and sufficiency of the touched-file selected tests over actual tracked and untracked files since the feature base. It reuses a complete applicable native result (host, CI or the normal commit hook) whose source, test, argv and runtime inputs are unchanged, citing its original operator and run; it executes only missing or affected checks, once, and records each run it executes with nwdes review observation add. nwdes never selects or runs tests. Reuse never waives a check. The host owns the live RED and GREEN observations of declared commands, recorded separately as host evidence, and the root does not repeat them. A documentation, authority or review-record commit alone is not a rerun trigger. An absent selector or an empty selection is a result to record, not a waiver. Never pick tests from memory. Missing observations, host observations not run, or failing selected tests are findings.

   ```sh
   nwdes prompt --role nw-software-crafter-reviewer --handoff "$H" --diff "$OUT/candidate.diff" --commit HEAD
   ```

   The final reviewer, not the root, records its own outcome through its generated verbs, for example:

   ```sh
   nwdes review observation add --feature search --subject candidate --text-file "$OUT/reviewer-run.txt"
   nwdes review close --feature search --subject candidate --outcome accepted --diagnostic "Whole candidate reviewed"
   ```

9. Obtain the examiner verdicts.

   After candidate review, build the examiner's complete bundle without host observations or root context. It names a public-only workspace of committed public documents and scratch, plus nwdes examine read and nwdes examine probe. The examiner gathers its own observations there, records each through the generated examination recording verbs before citing it, judges every fixed expectation from the user's point of view, and closes. Supply public inputs, never review, diff or producer verification.

   ```sh
   nwdes prompt --role nw-user-examiner --task examine --handoff "$H"
   ```

## Genuine product questions

Only when a genuine ambiguity or trade-off needs the product owner, build its discuss bundle and return the actual question and public product evidence. If bounded Quint exploration is relevant to that question, the host owns a model-capable native helper: supply the Request, PO diagnostic, actor observations, public authority and an authorized scratch directory outside the repository, never private implementation/oracle/review evidence. The helper authors the executable model and deterministic domain renderer, preserves trace indices, and reports unsupported actions. It probes available tools/help, typechecks, explores with explicit seed and bounds, and checks known ordering and unsupported-action cases. Return literal argv, tool versions, exits, outputs, raw and rendered traces, source identities, assumptions and unresolved choices to the same PO. Written-but-unrun work is not evidence; no invented traces, LLM-paraphrased mechanical rendering, authority edits or unauthorized installs. Installation or explicit human waiver follows the existing policy; a missing model while a checker is available is a helper task, not tooling unavailability. The PO/human decides product intent; architecture's separately required verification remains applicable.

## Verbs

This manually maintained skill is the workflow authority for the route above; it is not generated from the runtime. The runtime grammar and API help come from `nwdes --help` and `nwdes <group> <verb> --help`, which describe arguments, refusals and examples. Optional APIs are not route steps.

## Test-time strategy

Default budgets need no statement or measurement in a design. Timing evidence is required only when a test reaches half its budget or a derogation is requested; then retain nine sequential runs, median and maximum. The default CI suite stays within 300 s unless an Accepted repository ADR changes the ceiling or a human explicitly overrides one run. Only a human grants extra time or an infrastructure suite through the feature's Accepted derogation ADR; never a per-test permission. Keep a fast pure-core projection of each law in the default suite, use reliable test-impact selection locally, and split an over-budget component rather than hide it. Real adapter fault injection belongs only in that feature's granted infrastructure suite.

## After the run

Measure the run afterwards from the host session. Measurement is not a route step.
