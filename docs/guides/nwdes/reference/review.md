# review

Reviewers gather their own evidence on the named committed candidate. nwdes records their observations and findings; it never selects or runs tests. Review run records are separate from the canonical handoff.

## Scope

Every review verb takes `--subject` and the normal repository/project/feature or epic roots. Run from the checkout top level; omitted roots default to that checkout.

| Subject | Slice | Published record under the feature's `runs/` |
|---|---|---|
| `oracle` | Required `--slice S<n>` | `review.oracle.S<n>.json` |
| `slice` | Required `--slice S<n>` | `review.slice.S<n>.json` |
| `candidate` | No slice | `review.candidate.json` |

The first add, set or remove creates a draft. `open --from-current` revises an already published record: it carries the published findings and no observations, because a new round judges the bytes it is opened on and records its own. A refused close retains the draft; successful close publishes and consumes it. `abort` discards the scoped draft.

## Observations

```sh
nwdes review observation add --feature search --subject candidate --text-file /outside-checkout/reviewer-run.txt
nwdes review observation set --feature search --subject candidate --id R1 --text 'Actual corrected argv, exit, stdout and stderr'
nwdes review observation remove --feature search --subject candidate --at 1
```

`add` and `set` take `--text T` or `--text-file PATH`, containing the reviewer's actual run evidence. Text is retained literally. Record the mechanical touched-file selection and selected tests at the reviewed commit, including empty selection, incomplete selection or no selector found. Missing, unrun or failing evidence is a finding.

nwdes issues `R1`, `R2`, and subsequent observation IDs; the reviewer never chooses an ID. IDs are not reused after removal within a draft. `set` retains the selected ID. `set` and `remove` select by `--id R<n>` or one-based `--at N`.

The counter is draft-only and is not published in the review record. A reopened review does not carry the published observations, so its draft starts with none; its counter starts after the largest R ID of the published record, or at R1 when that record holds none, so a new round's IDs never repeat a published one. Within a draft, neither `set` nor `remove` changes the counter.

At recording, nwdes stamps the observation with git HEAD and cleanliness. Neither stamp is a CLI field. Only the selected feature's directory (its documents, `.nwdes-drafts/` and `runs/` records) and git-ignored paths are exempt from evidence cleanliness; staged changes, tracked edits and other untracked files are dirty. A run recorded dirty remains stale after the tree is cleaned. Revision through `set` stamps the corrected observation anew.

## Findings and close

```sh
nwdes review finding add --feature search --subject candidate --location src/cart.py:12 --obligation 'The declared rule' --observation 'What the reviewer observed' --owner implementation --remediation 'The required correction'
nwdes review close --feature search --subject candidate --outcome rejected --diagnostic 'Findings recorded'
```

Finding fields are `location`, `obligation`, `observation`, `owner`, and `remediation`. Owners are `oracle`, `design`, `implementation`, or `product`. Existing finding set/remove and open/abort verbs retain their normal semantics.

`obligation` names the approved obligation or applicable rule the finding is measured against. A point that cites none is a note in the reviewer's summary, not a finding; do not record it as an obligation. nwdes does not check this.

A published review carries its commit, observations and their stamps, findings, outcome and diagnostic. Close refuses `ReviewUnobserved` if no observation exists. It refuses `StaleObservation` for every observation whose commit differs from HEAD, whose recording stamp was dirty, whose close is on a dirty candidate, or, in an oracle review, whose oracle content differs from the close's. The feature directory is not dirty evidence. The oracle and its supports are judged by content, so they need not be committed. The diagnostic names all affected R IDs together. Rerun selection and tests at the reviewed commit and record them before closing again. Nothing is published on refusal.

An accepted candidate close (and an indeterminate one) on clean HEAD also refuses `OracleChanged: S<n>` for each slice whose oracle review was published with content, when the committed oracle or support bytes at HEAD differ from the approved bytes. The refusal names the changed paths, the approval commit (`git show <commit>:<path>` restores each approved file it holds), and each other slice that also declares a changed path. Identical bytes, or a slice with no oracle review record, are not checked. The refusal publishes no candidate record. A rejected candidate close is recorded without this check, because a rejection approves nothing.

Append permission. An oracle approval of a slice that declares both `--report` and `--mutants` also records the approved length and digest of each declared file (the oracle, its supports and the mutants file). A later change that only appends to those files is then accepted by the oracle check, in the accepted close, the rejected close and the crafter prompt, when every approved prefix still holds (`digest(current[:length])` equals the recorded digest) and the declared files are the same set. An in-place change, a removed line, or a changed declaration is still refused with `OracleChanged`. The live run and the mutant runs still hold each approved identity, so an append that changes an approved identity's outcome, or that shadows the function under test, is refused by those checks. A record written before this permission (it carries no prefix) keeps the whole-file rule until its oracle next changes. No stored copy of the approved bytes is kept.

The crafter prompt of a slice with identities runs those identities on a copy of the working tree before it renders, the same live run and mutant runs a candidate close makes, so uncommitted product bytes that fail an approved identity refuse the prompt with the identity refusal (`OracleIdentityChanged`, `MutantSurvives`). The working-tree copy is not a sandbox, as for every declared command.

The append permission does not check identities that an appended file adds: a new identity is not approved until its own slice is approved; nwdes runs it with the others but holds it to nothing. An undeclared file in the directory of an approved oracle is refused only where a declared mutant exposes it: a conftest that vacuates an approved assertion is refused, one that rebinds a single-identity check is accepted (the residuals in the decision record).

An oracle approval of a slice that declares `--report <junit path>` (see the slice reference) runs the slice's verification commands in the working tree, reads the JUnit XML report they write, and records every identity the report names with the outcome it observed (`classname::name`, outcome `pass`, `fail` or `skip`; a testcase absent from the report is not an identity). An approval whose report is missing, unreadable or names no identity refuses with `ReportMissing: S<n>` or `ReportEmpty: S<n>` and records nothing. A slice without `--report` records no identity and keeps today's whole-file rule alone.

An accepted or indeterminate candidate close also reruns those commands on the committed candidate (HEAD, extracted to a temporary folder), and every identity the approval recorded must report `pass`. A `fail`, a `skip` (a skipped or xfailed testcase is reported as skipped), or an identity the report does not contain refuses with `OracleIdentityChanged: S<n>`, one refusal for each identity, naming its outcome. A close whose approval recorded identities for a slice that no longer declares `--report` refuses with `ReportUndeclared: S<n>`. A rejected close runs none of this, because a rejection approves nothing.

This changes the design note's wording "each approved identity must keep its approved outcome" to "every approved identity must pass at the candidate". The reason is the workflow: an oracle is approved while it is RED, so the approval observes `fail` for the identities the product does not yet satisfy, and the candidate must make them pass. Holding the approved outcome would refuse every candidate that completes its work.

The `--mutants` file is a JSON list of `{path, old, new, targets}`: `path` is a product file, `old` must occur exactly once in it, `new` replaces it (it may be empty) and `targets` lists the identities the mutant must make fail. An approval refuses `MutantUntargeted` for each reported identity that no mutant targets, `MutantTargetUnknown` for a target the report does not name, and `MutantsMalformed` for a file that is not such a list. Mutants are checked on each accepted or indeterminate candidate close: `old` must occur exactly once (`MutantNotApplied` otherwise), and each targeted identity must then report `fail` on a copy of the candidate; one that passes, is skipped or is not reported refuses with `MutantSurvives`.

The approval stores no copy of the declared files. The refusal for a changed oracle names the restore command from the approval commit (`git show <commit>:<path>`), and that is the only restore offered.

Limits of the mutant check. A mutant is a text replacement, so it shows that a targeted identity depends on the changed text, not that the identity checks the whole behaviour.

The declared commands run with your permissions. A copy of the checkout is not a sandbox: it isolates nothing from the filesystem, the network or child processes, and an absolute path in a command reaches outside the copy. The slice writes the command, so an agent that writes a slice can write the command; review the `--command`, `--report` and `--mutants` of a slice as code.

On Windows the declared command is split with POSIX shell-word rules, so a backslash in it is an escape: write paths with forward slashes. The copy and the process start are exercised on Linux only in this delivery's tests; Windows is not tested.

Limits. nwdes checks only the identities the declared report names. It cannot judge what the report leaves out, nor whether a passing identity checks the behaviour beyond what its declared mutants show. The report must be JUnit XML: pytest writes it with `--junitxml=<path>`, `gotestsum --junitfile <path>` writes it for `go test`, `jest-junit` writes it for Jest, and a shell check writes it by hand, as the acceptance fixtures do. The declared commands run on the host with its privileges and no sandbox, each for at most 120 seconds; a timeout counts as no report. A flaky identity can refuse a candidate by chance: fix the test so it is deterministic, or rerun the oracle review on the committed bytes once the flake is fixed. Identities are compared as the report writes them, so renaming a test refuses the candidate until the approval is rerun.

## Owner-addressed reads

A rejected close prints one line for every owner present:

```text
OWNER implementation nw-functional-software-crafter FINDINGS 1,3
```

Finding ordinals are one-based positions in recorded order. Each owner line is followed by its scoped `nwdes review findings --owner O` read command. Native contact to each owner is the default; nwdes prints the owner lines to the root as a copy only, never as a relay. The root route is a fallback only when no native contact exists.

| Owner | Role |
|---|---|
| `oracle` | `nw-acceptance-designer` |
| `design` | `nw-solution-architect` |
| `implementation` | `nw-functional-software-crafter` for functional design; otherwise `nw-software-crafter` |
| `product` | `nw-product-owner` |

```sh
nwdes review findings --feature search --subject candidate --owner implementation
```

An owner reads exactly its own findings, in recorded order, with location, obligation, observation and remediation. The read prints `None.` if that owner has no findings. It changes no file and reads the published record, never a draft. If no record exists, `MissingFact` names the expected `runs/` file and explains that `nwdes review close` publishes it.

## Prompt admission

Build reviewer bundles with `nwdes prompt ... --commit REV --diff FILE`. The bundle names the resolved full commit and touched files and tells the reviewer to gather and record its own evidence. Unavailable git reports `InputUnreadable` naming the query.

`--observation` and `--observation-file` are retired on prompt and packet, including `--name=value`; `SelfGatheredEvidence` wins before argument parsing or named input reads. Abbreviations are unknown arguments. Reviewers record their observations through review verbs instead; no packet has a host Observations section.

See [prompt](prompt.md), [packet](packet.md), and the [delivery guide](../deliver-feature.md).
