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

A published review carries its commit, observations and their stamps, findings, outcome and diagnostic. Close refuses `ReviewUnobserved` if no observation exists. It refuses `StaleObservation` for every observation whose commit differs from HEAD, whose recording stamp was dirty, whose close is on a dirty candidate, or, in an oracle review, whose oracle content differs from the close's. The feature directory is not dirty evidence. The oracle and its supports are judged by content, so they need not be committed. The diagnostic names all affected R IDs together. Rerun selection and tests at the reviewed commit and record them before closing again. Nothing is published on refusal.

A candidate close on clean HEAD also refuses `OracleChanged: S<n>` for each slice whose oracle review was published with content, when the committed oracle or support bytes at HEAD differ from the approved bytes. Identical bytes, or a slice with no oracle review record, are not checked. The refusal publishes no candidate record; rerun the oracle review on the bytes to commit, then commit them.

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
