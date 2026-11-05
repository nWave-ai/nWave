# Deliver a feature with nwdes

**Audience.** The steps below are the operating procedure of the root assistant — the session you talk to. The assistant runs every `nwdes` command and orchestrates the roles; the person reads along, makes the scope and trade-off decisions the route asks for, and points the assistant at this guide — the sentence to paste is in [For your assistant](../README.md#for-your-assistant).

Use this guide to deliver a Request through an isolated lane, executable oracles, optional embedded slice feedback, one fresh whole-candidate final review and source-blind examiner verdicts. Start in the main worktree with an installed coding host, the project tool environment active, Git 2.38 or newer, and the intended existing trunk configured under `lanes.trunk`. The examples use feature `search`; replace its sample Request, value and project paths with the actual task.

Lanes are optional in an isolated checkout. For a lane-free delivery, the roles run in the current clean checkout and the orchestrator (the root assistant you are talking to) commits the GREEN candidate; skip lane open, compose and integrate, and review and examine that committed candidate. No lane-free flag is needed.

- The root writes product facts and promises itself.
- Every new product slice cites existing Request promises with repeatable `--promise P<n>`; product close requires every slice linked and every promise covered. Independent slices and any work size are valid.
- Ask the product owner only on ambiguity or a genuine scope or trade-off question.
- When the Request already states the outcome, no product owner turn or Quint model is required as a product prerequisite.
- There is no separate oracle review beyond the independent approval of each public oracle before craft, an artifact-quality check of that oracle alone; no per-slice charter.
- Run a separate design review only when a shared decision or ADR changes, as nwdes delta computes; otherwise no separate design review is needed.
- Embedded refinement review of a GREEN slice is optional risk-reducing feedback; use it when a slice warrants it.
- When used, build the embedded review with `--diff` from the slice's base commit and `--slice S<n>`; record it with `--subject slice --slice S<n>`.
- After all slices are GREEN, the final whole-candidate review is by a fresh independent reviewer, never the embedded reviewer.
- Record the final review with `--subject candidate`.
- The final reviewer does not consult embedded review records.
- An embedded approval never counts as the final review.
- One source-blind EXAMINE judges the complete Feature, never an individual slice.
- The examiner never receives producer discussions or embedded findings.
- The examiner returns its verdicts once, on the whole candidate revision assembled across slices, before integrate.
- Order: compose, then the final whole-candidate review is accepted, then source-blind EXAMINE, then integrate. Independent implementation and verification may run in parallel; the final review and EXAMINE never run speculatively.
- The independent approval of each oracle before craft stays; the final whole-candidate review still covers the oracle.
- Use one slice by default when one behaviour suffices; each slice delivers one observable behaviour a reviewer judges in one short pass.
- The route's guidance is to keep a feature to at most 5 slices; the CLI enforces no ceiling.
- The first slice is the one walking skeleton and every later slice extends it with explicit dependencies.
- The Request keeps its whole value and shared design.
- A technical layer or mocked interaction is not a slice.
- On a rejected close, nwdes prints every finding owner's role and read command together.
- Each owner reads exactly its own findings from the published review record through `nwdes review findings --owner O`. Native contact to each owner is the default; nwdes prints the owner lines to the root as a copy only, never as a relay.
- Owners converge through their records and direct messages.
- Each owner edits only its own artifact with its own verbs and records only its delta with `open --from-current`.
- A revised oracle needs independent re-approval, an artifact-quality check of that oracle alone, with its observed semantic RED before the crafter aligns production.
- When embedded review was used, the same embedded reviewer confirms each finding against the corrected revision by reopening its own `--subject slice` record with `open --from-current`, recording its own observation of that revision with `review observation add`, using `finding remove` for confirmed findings and closing accepted only when every finding is confirmed.
- The root rebuilds only the bundles `nwdes delta` lists AFFECTED, without a full handoff pass.
- A refuted fix or an owner disagreement leaves the finding open and escalates to the host; never record it closed.
- Before every review (oracle, embedded, final, or design only when a shared decision or ADR changes), the reviewer runs existing tests selected by the project's mechanical selector from actual tracked and untracked touched files at the named commit. nwdes never selects or runs tests.
- Use oracle/support files since slice base for oracle review; slice files since slice base for embedded review; assembled candidate files since feature base for final review; design files named via root-context for design review only when a shared decision or ADR changes.
- The final reviewer owns selection and sufficiency of the touched-file selected tests. It reuses a complete applicable native result (host, CI or the normal commit hook) whose source, test, argv and runtime inputs are unchanged, citing its original operator and run; it executes only missing or affected checks, once. Reuse never waives a check. It records argv/exit status/stdout/stderr of each run it actually executes with `nwdes review observation add`; nwdes stamps each observation with the reviewed commit. Explicitly record empty selection, incomplete selection or no selector found. The root supplies no observation to a reviewer.
- An observation is never carried into a reopened review: a reviewer that reuses an earlier run records a new observation that cites the run's original commit, argv, exit and output, and a changed candidate requires new observations.
- Missing touched-file observations or failing selected tests are findings.
- Never pick tests from memory or omit failing selected tests.

Give each role the complete bundle from `nwdes prompt`. Every bundle states the resolved Jev authorization: `authorized` by default, or `unauthorized` when the call or a configuration tier refuses it (`--jev unauthorized`, or `"jev": "unauthorized"` in `~/.nwave/config.json` or the repository's `.nwave/config.json`; the flag wins; nwdes never writes the key). Each role uses its kind's nwdes CLI verbs and closes its record. Crafters use `nwdes craft`; reviewers use `nwdes review`. nwdes keeps their run records; the root keeps no reply copy and submits no role output. Return a refusal to its owner; do not invent missing values.

The orchestrator decides when and how to commit: normally one plain `git commit` of a GREEN slice with hooks on. The optional [`nwdes commit`](reference/commit.md) commits a role's owned files, including its run record. nwdes imposes no commit after a close and none before craft, and several authority closes may stand uncommitted at once. Keep the index empty before the commit. The root keeps lane open, compose and integrate. Plain Git commits remain available to humans and outside nwdes deliveries.

There is one optional charter per complete Feature, never per slice. One source-blind EXAMINE covers the complete Feature, never per slice. To obtain the optional charter, build `nwdes prompt --role nw-product-owner --task charter` and record it with `nwdes charter` verbs, without naming a slice.

Run every nwdes command from the top level of the checkout. Roots default to cwd and the repository root; lane verbs resolve the main worktree. The first add, set or remove creates the scoped draft. Use `open --from-current` to revise current authority; close without a draft validates empty values. nwdes builds every draft, identity and serialized record itself and refuses an incomplete or malformed record before that record is written, so each step behaves deterministically: the wrong state is hard to write, never repaired afterwards.

## Steps

1. Open the lane first.

   Keep existing `.nwave/config.json` settings and name the actual existing trunk branch in `lanes.trunk`; `main` is an example, not a default. Store temporary evidence outside the worktree.

   ```sh
   ROOT=$PWD
   LANE="$ROOT/lanes/search"
   OUT="$HOME/.cache/nwdes/search"
   mkdir -p "$OUT"
   nwdes lane open --feature search
   ```

2. Create the feature inside that lane.

   Enter the lane's top level before creating the feature. Preserve the Request verbatim and choose value and size independently from route. Use the handoff path this command prints if destination configuration differs from the default below.

   ```sh
   cd "$LANE"
   nwdes feature new --feature search --request Search --size M --value Find
   H="$LANE/docs/feature/search/handoff.json"
   ```

3. Write root product facts and promises.

   Record the public promises and the smallest sufficient slice plan with the [root product commands](reference/index.md#role-recording). Ask the product owner only when a product decision is needed; give it the complete bundle from `nwdes prompt`. It records with the same CLI and closes.

   Record the facts, link each slice to promises it serves, then close. Missing or unknown links refuse before draft writes; close also refuses uncovered Request promises and a missing scope-out line (`nwdes product scope-out add --text TEXT`). Correct links, add a justified promise with `nwdes product promise add`, or split unrelated outcomes into a separate `nwdes feature new`.

   ```sh
   nwdes product promise add --feature search --kind Outcome --text 'The search result is returned'
   nwdes product slice add --feature search --observation Find --promise P1
   nwdes product close --feature search --outcome accepted --diagnostic 'Public facts recorded.'
   ```

   Check the split before closing: does every slice contribute to this one value, or did you bundle unrelated outcomes? Do not answer yes by default. Split unrelated outcomes into a separate nwdes feature new.

4. Record the design.

   Retain the previous handoff before the architect starts. Give the architect its complete prompt bundle. It records with the design verbs and closes; the close refuses until each code target has a reuse and an impact decision and the design has its architectural and contract test records or reasoned not-applicables ([design reference](reference/design.md)). The orchestrator commits its architecture, ADR and handoff files when it chooses. Run a separate design review only when the delta shows a shared decision or ADR change.

   ```sh
   cp "$H" "$OUT/before-design.json"
   nwdes prompt --role nw-solution-architect --handoff "$H"
   nwdes delta --previous "$OUT/before-design.json" --new "$H"
   ```

   Preserve assigned IDs. Retain accepted ADR declarations by key with unchanged bodies or replace explicitly with an accepted successor. Use the [design reference](reference/design.md) for identity, duplicate-slot, program-resolution and withdrawal rules.

5. Fix examiner expectations once.

   Give a fresh examiner the complete expectations bundle inline. It works from the user's point of view and needs public product facts. It records with the expectations CLI verbs and closes. Use the assigned expectation IDs in later observations.

   ```sh
   nwdes prompt --role nw-user-examiner --task expectations --handoff "$H"
   ```

6. Record the slice's acceptance oracle.

   Give the acceptance designer for S1 its complete bundle. It writes only the named oracle and supports, never production. It records acceptance rows with the CLI and closes; the orchestrator commits its oracle, supports, acceptance documents and handoff when it chooses. Repeat this stage and craft for each designed slice. Preserve obligations that are already satisfied.

   For each test, record with `--still-passes-if` the nearest plausible wrong behaviour it would still accept, and tighten the test when that behaviour violates its promise.

   ```sh
   nwdes prompt --role nw-acceptance-designer --handoff "$H" --slice S1
   ```

7. Craft the slice and observe GREEN.

   Use a real observed RED baseline for the declared commands; run them when no earlier trusted observation supplies it, never merely to confirm a reported failure. A setup or collection failure is not the intended failing assertion. Retain runner-derived observed, failed-assertion and setup-failure counts. If DESIGN declares prefactoring, preserve its before-move and after-move-before-behavior evidence before changing behaviour.

   Invoke the functional crafter for a functional design, otherwise the software crafter. Give it the exact bundle and owned targets; it never edits the oracle. It records through `nwdes craft` and closes with its own explicit `--role`, as its generated reference shows. nwdes keeps the actor in the private receipt, not the run record; the root keeps no reply copy. The host's live observations cover each slice's declared commands, recorded once per candidate; a changed candidate needs new observations. Keep every test file collectable.

   ```sh
   nwdes prompt --role nw-functional-software-crafter --handoff "$H" --slice S1
   ```

   The orchestrator commits the crafter's slice when it chooses. Capture its complete diff from its base commit in `$OUT/slice.diff`. If embedded review is used, the reviewer gathers its own native evidence at clean HEAD:

   ```sh
   nwdes prompt --role nw-software-crafter-reviewer --handoff "$H" --slice S1 --diff "$OUT/slice.diff" --commit HEAD
   ```

   If embedded review is used, the embedded reviewer records its own outcome through its generated verbs, for example:

   ```sh
   nwdes review observation add --feature search --subject slice --slice S1 --text-file "$OUT/reviewer-run.txt"
   nwdes review close --feature search --subject slice --slice S1 --outcome accepted --diagnostic "Embedded findings confirmed"
   ```

8. Run one fresh independent final whole-candidate review.

   After all slices pass, the orchestrator commits them when it chooses and the root composes the lane. Retain printed EXPECTED and CANDIDATE identities. Capture the whole diff from the feature base in `$OUT/candidate.diff`, including approved oracle and support changes. The final reviewer owns selection and sufficiency of the touched-file selected tests on that clean committed candidate. It reuses a complete applicable native result (host, CI or the normal commit hook) whose source, test, argv and runtime inputs are unchanged, citing its original operator and run; it executes only missing or affected checks, once. Reuse never waives a check. The host's live observations cover declared commands; affected checks remain required, and a changed candidate needs new observations.

   ```sh
   nwdes lane compose --feature search
   nwdes prompt --role nw-software-crafter-reviewer --handoff "$H" --diff "$OUT/candidate.diff" --commit HEAD
   ```

   The final reviewer owns selected-test execution and the approval evidence. It gathers that evidence at the named commit: mechanical touched-file selector and selected tests, recording actual argv, exit, stdout and stderr with `nwdes review observation add`. The observation explicitly reports when no selector exists or selection is incomplete; an empty selection is a real result. Missing, unrun or failing evidence is a finding. nwdes stamps observations with HEAD and cleanliness; no host observation flag is admitted. Bash permits those runs, authorized Jev and all generated scoped review verbs without candidate edits. The reviewer records and closes even when Jev is unauthorized; nwdes keeps the run record and the root keeps no reply copy. Rejected close prints owner roles; each owner reads exactly its own findings with `nwdes review findings --owner O`, without a root relay.

   The final reviewer records its own outcome through its generated verbs, for example:

   ```sh
   nwdes review observation add --feature search --subject candidate --text-file "$OUT/reviewer-run.txt"
   nwdes review close --feature search --subject candidate --outcome accepted --diagnostic "Whole candidate reviewed"
   ```

9. Obtain examiner verdicts after the final review is accepted.

   Give a fresh examiner its complete bundle inline without host observations or root context. The bundle names a public-only workspace projecting committed public documents and initially empty scratch, plus `nwdes examine read` and `nwdes examine probe`. The examiner gathers its own observations there, records each through its generated examination recording verbs before citing it, then judges every fixed expectation and closes. Never supply producer checks, diffs or review judgments. The read/probe boundaries do not confine the examiner's own plain Bash process.

   ```sh
   nwdes prompt --role nw-user-examiner --task examine --handoff "$H"
   ```

   Resolve each unmet expectation as an oracle gap, product violation, expectation defect or observation gap; do not change expectations to fit the implementation.

10. Integrate the accepted candidate.

   Use the unchanged identities from compose after verification, accepted review and successful public examination of that same candidate. If trunk or candidate changed, reconcile and reassess affected evidence before retrying. Classify every remaining lane file before integration; disposal is deliberate authorization to delete, never a way to hide user work. Integration also removes the lane. After an effect failure, rerun the same integrate command with the same values.

   ```sh
   nwdes lane integrate --feature search --expected "$EXPECTED" --candidate "$CANDIDATE"
   ```

## After the run

Measure the run afterwards from the host session. Measurement is not a route step.

**Done:** each declared check has a host GREEN observation or a reused observation with unchanged inputs, the accepted final review records its selected-test runs, fixed expectations have real public observations and successful examiner verdicts, and the accepted candidate is integrated. The host chooses sequencing; nwdes constructs artifacts and reports facts, never selects a next action.

See the [command reference](reference/index.md), [lane contract](reference/lane.md), [prompt contract](reference/prompt.md) and [packet contract](reference/packet.md) for lookup details.
