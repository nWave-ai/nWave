# v3 and v4 compared

> **History page (v3 and v4).** This page compares the 3.x and 4.x delivery models. Names such as `roadmap.json` and `execution-log.json` describe the 3.x runtime, which v4 removed; they appear here only to explain that history. For the upgrade, read [Migrate from nWave 3.x](migrating-from-3x.md).

You know nWave 3.x and you are adopting 4. This page explains, side by side, how each version structures delivery: who plans the work, who writes the tests, what a crafter implements in one turn, and how commits and integration happen. It answers the two questions adopters ask most: *do crafters implement a whole slice at a time in v4?* and *can I get one pull request per piece of deliverable work?* It also shows where v4 keeps the quality limits, the readable documents and the 3.x hook cleanup. For upgrade steps, see [Migrate from nWave 3.x](migrating-from-3x.md); for the full change map, [What's new in v4](whats-new-v4/README.md).

## How v3 delivered work

v3 broke a feature into seven waves — discover, diverge, discuss, design, devops, distill, deliver — each driven by a `/nw-*` command and a specialized agent. Every wave produced artifacts you reviewed before the next one ran. DISTILL then DELIVER always closed the feature: the acceptance designer wrote the feature's acceptance tests first, as Given-When-Then `.feature` files, and DELIVER turned them into code.

Inside DELIVER, an architect first wrote a `roadmap.json` (a file v4 retires): an ordered list of steps with IDs like `01-01`, each step mapped to scenarios from the tests that already existed. Each step went to a crafter through the DES runtime — v3's enforcement layer — which enforced a three-phase cycle per step: RED, GREEN, COMMIT. A step was finished when its phases were in the execution log and its commit existed; the acceptance suite ran again after every step. When all steps were green, feature-level phases followed: a full integration gate, a refactoring pass over everything the feature touched, adversarial review, optional mutation testing, integrity verification of the execution log, and one final commit-and-push.

So in v3 the unit of crafting was a roadmap step, committing was part of each step's TDD contract, and a feature ended in a single push.

## How v4 delivers work

v4 removes that runtime. Delivery now runs through **nwdes**, a command that keeps one canonical handoff per feature — a JSON file recording the feature's facts — and generates role prompts, documents and review packets from it. nwdes makes no model calls and enforces no gates: the host — the coding tool that runs the models — invokes the roles and runs each slice's declared verification commands; the root assistant, the session you talk to, reads the results and decides sequencing. Humans decide scope and trade-offs.

The work is cut into **slices**: a slice is one observable behavior of the feature, tied to the promises the feature made. The first slice is the feature's walking skeleton — one thin public path end to end — and every later slice extends that same skeleton. The route advises one slice when one behavior suffices, and at most five slices per feature as guidance; the command line enforces no ceiling.

Per slice, the loop is small. The acceptance designer writes that slice's executable public oracle — an oracle is the test that observes the promised behavior through the public surface — and an independent reviewer approves it before any code. Then the crafter is invoked with exactly that slice's ordered work list, and must bring the oracle from RED to GREEN (observed failure before implementation, pass after) through the real driving port — the public entry point callers use — before another slice starts. The orchestrator, not the crafter, commits: normally one plain commit of a green slice, and each refactor committed alone and green. After all slices are green, one fresh independent review and one source-blind examination (EXAMINE) judge the whole feature, and the feature's lane — an optional per-feature worktree — is integrated back into trunk in a single fast-forward.

## Side by side

| | v3 | v4 |
|---|---|---|
| Unit of craft | roadmap step (`01-01`) mapped to pre-written scenarios | slice: one observable behavior, tied to a promise |
| Acceptance tests | whole feature written first, in the DISTILL wave | oracle written per slice, just before craft; no speculative scenarios |
| Who writes tests | acceptance designer; crafter implements only | unchanged — the acceptance designer owns every test; the crafter never edits the oracle |
| Crafter receives | one roadmap step, dispatched through the DES runtime | one slice's ordered work, from an nwdes-generated prompt |
| Walking skeleton | at most one per feature | exactly one, created by the first slice and extended by every later one; it also drives the implementation |
| Commits | COMMIT phase inside each step's TDD cycle; one push at the end | orchestrator decides; normally one commit per green slice; refactors committed alone and green |
| Enforcement | DES runtime: phase gates, execution log, integrity verification | nwdes records facts and enforces nothing; the host observes RED then GREEN; independent review and EXAMINE once per feature |
| Feature-end gates | adversarial review, optional mutation testing, integrity verification of the execution log | one fresh independent review and one source-blind examination (EXAMINE); their limits are counts the project sets |
| Documents for people | none; each wave produced artifacts for its reviewers | readable pages with described diagrams, on by default in English; `--documents no` turns them off |
| Integration | feature finalize: one commit-and-push | one lane integrate per feature (fast-forward trunk); lanes are optional |

## Do crafters implement a whole slice at a time?

Yes. In the documented route the crafter is invoked once per slice, receives only that slice's work, and finishes it before another slice starts. A slice is deliberately small — one observable behavior — and a crafter that cannot complete its slice rejects with the concrete gap instead of half-delivering. The walking skeleton makes the first slice thicker than it looks: it wires the real adapters end to end, and it also drives the implementation of the domain logic and application services it needs. Every later slice extends that one skeleton, and every scenario outside the skeleton runs in memory through the driving port.

## Can you get one pull request per piece of work?

Not from the framework — that is the honest answer. Neither version has a pull-request step: v3 ended in one commit-and-push per feature, and v4 ends in one integration per feature. What v4 does give you is clean cut points: the documented commit norm is one commit of a green slice, and every refactor lands as its own green commit. Those commits are pull-request-shaped, so you can build a per-slice pull-request flow on top of them with your own tooling. That flow is your workflow choice: nWave does not create, size or guarantee pull requests, and no version promises that every intermediate commit is deployable on its own. Treat "one pull request per slice" as an open adoption question. You can calibrate it by running one feature, observing where the slice commits land, and then setting your own rule.

## Quality limits: reviews and examinations

v3 fixed its feature-end gates: adversarial review, optional mutation testing, integrity verification. v4 lets each project set two limits itself, and both are counts.

The review limit says how many rounds a finding may take: one to five. The examine level says how many examinations a delivery admits. It has three names: `quick`, `standard` and `extended`. `standard` is the built-in default. `quick` admits one examination and no repair round. `standard` admits two examinations and one repair round. `extended` admits three examinations and two repair rounds. A level limits only the examinations, in the same way the review rounds limit reviews.

What stays the same is the idea of v3's adversarial review: an independent judgement after the code exists. What is different is the form. The v4 examination is source-blind: the examiner reads the product from the user's side and has not read the code. For every expectation row the examiner sets one verdict: `met`; `unmet`, with a class that names the kind of gap; or `not_examined`, with a reason. The verdicts decide the outcome: an unmet row rejects the examination, a not-examined row leaves it indeterminate, and only an all-met set is accepted. A row not examined is never green. When the candidate commit moves after the examine prompt, the examination close is refused: the evidence holds only for the commit the examiner saw, so the prompt is rebuilt on the new commit first.

One honest limit: nothing blocks the integration of the lane when an examination did not pass. nWave records the verdicts; reading them and deciding is yours.

The dynamic route (`/nw-dynamic`) records its examination in its own step record: the examiner's id and one line per fixed row. That route's lines carry their own words — `pass`, `fail`, `not-examined`, `unstable` — where the spine's examination speaks of `met`, `unmet` and `not_examined`; the two vocabularies belong to their own routes and are not interchangeable.

## The rigor conversation

Both limits are set with one command: `nwave-ai rigor`. On a terminal it asks six questions, one at a time: the model for each role, the review rounds, the examine level, the documents for people, the document language — asked only when documents is `yes` — and the hosts. Each question says what it is, why to change it, its answers and its default. Enter keeps the value in effect. A wrong answer asks the same question again; it does not abort. A closed terminal, where no question can be asked, refuses once and names every question that has no answer. The answers go to `.nwave/config.json` in the repository; the global file is read, never written. `nwave-ai rigor --show` prints every value with its source and writes nothing.

## Readable documents for people who do not read code

v3's artifacts were for the engineers who reviewed each wave. v4 can also write pages for other readers: the owners, the operators, the sponsors. This output is new and on by default, in English. Answer `no` to the documents question of `nwave-ai rigor` to turn it off, or name another language there.

The product page of each feature (`brief.html`) shows the request, the work and the promises as short paragraphs, and declares its language as the page's language attribute. Each Mermaid diagram declares one description sentence inside its block. The page shows that sentence above the collapsed diagram source, so a reader who cannot see the picture still reads what it shows. A diagram with no description, with an empty one, or with more than 25 distinct nodes refuses the product owner's output: no page is written with a diagram a reader cannot use. Because the output is on by default, that refusal applies to every design until the diagram is fixed or the output is turned off. The `nw-diagram` skill holds twelve rules for readable diagrams — among them the title, the reading order, color contrast and short labels — and a documentarist asks the owners one round of questions about their recorded decisions.

Set `"documents": { "html": false }` in `.nwave/config.json` and no HTML page is written at all; the markdown briefs and the handoff stay as they are. `nwdes document --product` writes the project brief, and `nwdes document --overview` writes the project overview, which lists every decision file with its title, its status and a link.

## What the upgrade does to your 3.x hooks

Your attribution choice survives the upgrade: if you turned it off in 3.x, it stays off. The upgrade removes the Claude Code hook rows that run the retired 3.x runtime, whatever their matcher, and the `nwave_hook_version` stamp they carried. Hooks and keys you wrote yourself are kept.

Known defect: on Codex hosts a 3.x hook row can remain after the upgrade. The row is dead — it calls a runtime that v4 no longer ships, so it cannot do anything. nWave does not remove it, because on Codex nWave removes only the hook rows its own manifest proves it owns. You can delete the row by hand.

## Where to go next

| You want to | Read |
|---|---|
| Run a v4 delivery end to end | [Deliver a feature](nwdes/deliver-feature.md) |
| Check a slice, lane or commit verb | [slice](nwdes/reference/slice.md) · [lane](nwdes/reference/lane.md) · [commit](nwdes/reference/commit.md) |
| Set the review and examine limits | [nwave-ai rigor](../reference/cli.md#nwave-ai-rigor) |
| Turn on the readable pages | [Read architecture diagrams and the readable brief](readable-brief-and-diagrams.md) |
| Upgrade a 3.x install | [Migrate from nWave 3.x](migrating-from-3x.md) |
| Look up a term | [Glossary](glossary.md) |
