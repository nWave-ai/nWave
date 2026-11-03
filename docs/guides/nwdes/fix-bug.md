# Fix a bug with nwdes

**Audience.** The steps below are the operating procedure of the root assistant — the session you talk to. The assistant runs every `nwdes` command and orchestrates the roles; the person reads along, makes the scope and trade-off decisions the route asks for, and points the assistant at this guide — the sentence to paste is in [For your assistant](../README.md#for-your-assistant).

Use this guide for a reported defect whose expected public behaviour is known. Start in the main worktree with an installed coding host, the project's environment active, the intended existing trunk configured under `lanes.trunk`, and the original pre-fix revision available. The examples use a Python search component at `src/search.py`; substitute the actual defect, promise, owned target and declared verification command.

A single bugfix may use the current clean checkout without a lane. The roles run there and the orchestrator (the root assistant you are talking to) commits the GREEN candidate; skip lane open, compose and integrate, and review and examine the same committed candidate. No lane-free flag is needed. The steps below show the optional lane route.

The root writes product facts and promises itself through the slice command. Ask the product owner only on a genuine ambiguity, scope question or trade-off; when the Request already states the outcome, no product owner turn or Quint model is required as a product prerequisite. There is no separate oracle review beyond the independent approval of each public oracle before craft, an artifact-quality check of that oracle alone; no per-slice charter. Use one slice by default when one behaviour suffices. Run a separate design review only when a shared decision or ADR changes, as nwdes delta computes; otherwise no separate design review is needed.

Embedded refinement review of a GREEN slice is optional risk-reducing feedback. The final whole-candidate review is always required: a fresh independent reviewer, never the embedded reviewer, records it with `--subject candidate`, and it does not consult embedded review records. An embedded approval never counts as the final review. One source-blind EXAMINE judges the complete Feature, never an individual slice, runs after the final review is accepted, and receives no producer discussions or embedded findings. It returns its verdicts once on the whole candidate revision before integrate. The independent approval of each oracle before craft stays.

Give each role the complete bundle from `nwdes prompt`. Every bundle states the resolved Jev authorization: `authorized` by default, or `unauthorized` when the call or a configuration tier refuses it (`--jev unauthorized`, or `"jev": "unauthorized"` in `~/.nwave/config.json` or the repository's `.nwave/config.json`; the flag wins; nwdes never writes the key). Each role uses its kind's nwdes CLI verbs and closes its record. Crafters use `nwdes craft`; reviewers use `nwdes review`. nwdes keeps their run records; the root keeps no reply copy and submits no role output. Return a refusal to its owner; do not invent missing values.

The orchestrator decides when and how to commit, normally one plain `git commit` of a GREEN slice with hooks on; the optional [`nwdes commit`](reference/commit.md) commits a role's owned files, including its run record. nwdes imposes no commit after a close, so several authority closes may stand uncommitted at once. Keep the index empty before the commit. The root keeps lane open, compose and integrate. Plain Git commits remain available to humans and outside nwdes deliveries.

Run every nwdes command from the top level of the checkout. Roots default to cwd and the repository root; lane verbs resolve the main worktree. The first add, set or remove creates the scoped draft. Use `open --from-current` to revise current authority; close without a draft validates empty values. nwdes builds every draft, identity and serialized record itself and refuses an incomplete or malformed record before that record is written, so each step behaves deterministically: the wrong state is hard to write, never repaired afterwards.

## Steps

1. Open the lane first.

   Run from the main worktree. Preserve its existing `.nwave/config.json` settings and set `lanes.trunk` to the intended existing branch; `main` is an example, not a default. Keep temporary evidence outside the worktree.

   ```sh
   ROOT=$PWD
   LANE="$ROOT/lanes/search"
   OUT="$HOME/.cache/nwdes/search"
   mkdir -p "$OUT"
   nwdes lane open --feature search
   ```

2. Create the feature inside the lane.

   Enter the lane's top level before creating the feature. Keep the user's reported defect verbatim and choose value and size independently from route. If destination configuration differs, use the handoff path printed by this command instead of the default below.

   ```sh
   cd "$LANE"
   nwdes feature new --feature search --request Search --size S --value Find
   H="$LANE/docs/feature/search/handoff.json"
   ```

3. Write the slice and its promise.

   The root supplies the public observation, paradigm, oracle path, authorized target, stimulus, expected result, falsifier, promise and verification command. Omit `--slice` to create its assigned ID; later updates name that ID. The program must exist in the writer's environment. Here `python` comes from the activated project environment.

   ```sh
   nwdes slice set --feature search --observation Find --paradigm functional --oracle tests/search.py --stimulus Search --expected Found --falsifier Missing --command 'python tests/search.py' --promise 'The search result is returned' --extend src/search.py
   ```

4. Fix examiner expectations.

   Give a fresh examiner the complete expectations bundle inline. It works from the user's point of view and needs public product facts. It records with the expectations CLI verbs and closes. Use the assigned expectation IDs in later observations.

   ```sh
   nwdes prompt --role nw-user-examiner --task expectations --handoff "$H"
   ```

5. Record the acceptance oracle.

   Give the acceptance designer the complete slice bundle. It writes only the named oracle and supports, records acceptance rows with the CLI and closes; the orchestrator commits its files when it chooses. The public promise and falsifier, not implementation details, define the check.

   ```sh
   nwdes prompt --role nw-acceptance-designer --handoff "$H" --slice S1
   ```

6. Observe the intended failing behaviour RED.

   Use a reported pre-fix failure when it supplies the required declared observation; otherwise run the declared checks on the original pre-fix revision. Retain runner-derived observed, failed-assertion and setup-failure counts. The requested behaviour must fail as an assertion, not because imports, fixtures or dependencies are broken. Never rerun a user's reported failure merely to confirm it, and never make the tree uncollectable.

7. Craft the fix and observe GREEN.

   Invoke the functional crafter for a functional design, otherwise the software crafter. It changes only the owned targets and never edits the oracle. If DESIGN declares prefactoring, preserve its before-move and after-move-before-behavior evidence before changing behaviour. The crafter records through `nwdes craft` and closes with its own explicit `--role`, as its generated reference shows. The actor belongs only to the private receipt, not the run record; the root keeps no reply copy. The host records the same declared checks' GREEN observation on the fixed candidate once.

   ```sh
   nwdes prompt --role nw-functional-software-crafter --handoff "$H" --slice S1
   ```

8. Optional: embedded refinement review of the GREEN slice.

   The orchestrator commits the crafter's slice when it chooses. Capture its complete diff from the slice base as `$OUT/slice.diff`. If you use embedded review, the reviewer owns selection and sufficiency of the touched-file selected tests on the exact commit under review. It reuses a complete applicable native result (host, CI or the normal commit hook) whose source, test, argv and runtime inputs are unchanged, citing its original operator and run; it executes only missing or affected checks, once. Reuse never waives a check. The reviewer records each run it executes with `nwdes review observation add` before it closes the review.

   ```sh
   nwdes prompt --role nw-software-crafter-reviewer --handoff "$H" --slice S1 --diff "$OUT/slice.diff" --commit HEAD
   ```

   Each literal run text includes actual argv, exit status, stdout and stderr, including an empty or incomplete selection or absent tooling. The reviewer records it and its outcome through the generated scope, for example:

   ```sh
   nwdes review observation add --feature search --subject slice --slice S1 --text-file "$OUT/slice-verification.txt"
   nwdes review close --feature search --subject slice --slice S1 --outcome accepted --diagnostic "Embedded findings confirmed"
   ```

9. Run one fresh independent final whole-candidate review.

   The orchestrator commits the candidate when it chooses; the root composes the lane. Record the printed EXPECTED and CANDIDATE identities. Capture the whole diff from the feature base, including approved oracle/support changes, as `$OUT/candidate.diff`. The final reviewer owns selection and sufficiency of the touched-file selected tests on the exact commit under review. It reuses a complete applicable native result (host, CI or the normal commit hook) whose source, test, argv and runtime inputs are unchanged, citing its original operator and run; it executes only missing or affected checks, once. Reuse never waives a check. The host's live observations cover declared commands; affected checks remain required, and a changed candidate needs new observations. The reviewer records each run it executes with `nwdes review observation add` before it closes the review.

   ```sh
   nwdes lane compose --feature search
   nwdes prompt --role nw-software-crafter-reviewer --handoff "$H" --diff "$OUT/candidate.diff" --commit "$CANDIDATE"
   ```

   The reviewer judges its own actual argv, exit status, stdout and stderr, including empty or incomplete selection or absent tooling. Missing, unrun or failing evidence is a finding. Preserve candidate source/oracle bytes. Host owns models and checker execution. Bash only: the selector, the selected tests and all exact generated `nwdes review` recording verbs, including close. Authorized Jev remains optional; recording and closing remain mandatory when it is unauthorized. Resolve findings through their artifact owners before continuing.

   The reviewer records its run text and outcome through its generated scope, for example:

   ```sh
   nwdes review observation add --feature search --subject candidate --text-file "$OUT/native-verification.txt"
   nwdes review close --feature search --subject candidate --outcome accepted --diagnostic "Whole candidate reviewed"
   ```

10. Obtain the examiner verdicts.

   Only after the final review is accepted on the same candidate, give a fresh examiner the complete bundle inline, without observations. It reads public documents and probes public behaviour in the named workspace, gathers its own observations, records them with its generated examine verbs and closes. Resolve every unmet fixed expectation before continuing.

   ```sh
   nwdes prompt --role nw-user-examiner --task examine --handoff "$H"
   ```

11. Integrate the accepted candidate.

   Use the unchanged identities from compose after verification, accepted review and successful public examination of that same candidate. A changed trunk or candidate requires reconciliation and reassessment of affected evidence. Classify remaining lane files deliberately before integration; never authorize deletion merely to hide user work. Integration also removes the lane. After an effect failure, rerun the same integrate command with the same values.

   ```sh
   nwdes lane integrate --feature search --expected "$EXPECTED" --candidate "$CANDIDATE"
   ```

If new architecture decisions are genuinely needed, take an architect turn instead of hiding them in the short route. nwdes never chooses whether the defect is fixed or what action runs next; the host owns sequencing and each slice's RED/GREEN verification.

## After the run

Measure the run afterwards from the host session. Measurement is not a route step.

**Done:** the original behaviour has a real failure observation, the fixed behaviour passes, the accepted final review and independent findings are resolved, the examiner's verdicts meet the fixed expectations, and the accepted candidate is integrated.

See the [feature route](deliver-feature.md), [slice contract](reference/slice.md), [expectations contract](reference/expectations.md) and [lane contract](reference/lane.md) for related details.
