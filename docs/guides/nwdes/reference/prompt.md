# prompt

`prompt` prints one complete inline role bundle ending with the generated verb reference. It does not invoke a model. All roles use their kind's CLI verbs and close their record. Crafters record through `nwdes craft`; reviewers record through `nwdes review`. nwdes keeps their run records. The root keeps no reply copy.

Directory-bearing bundles print their working directory once and render invocation-derived authority and handoff paths relative to it. Stored model paths remain exactly as stored because they participate in retained identity. Source-blind examiner and charter recipes gain no directory source.
Recording instructions name the role's kind and task. The examiner works from the user's point of view and uses the same CLI as all other recording roles.
Structured path lists group equal directory prefixes, even when the original paths were nonconsecutive, and may print `Path prefix <prefix>:` once. Prepend it to each indented suffix to recover the exact complete path; unindented paths stand alone. Alias-to-path mappings and target/oracle/support order stay unchanged. Stored values are never normalized.


Typed TEXT is fenced verbatim; compact role/packet fences may omit the optional `text` language hint. Delimiters still exceed embedded backtick runs. Compact record sections use plain labels (`Decisions:`, `D1:`); labels in authored prose stay inside its fence. Repeated text receives a `[F<n>]` definition at first use; later occurrences refer to it, while single-use text needs no reference label. Request, public-oracle, command, observation and root-context carriers retain their verbatim contracts and existing line-end rules.

Acceptance reviewers, implementation and prefactoring crafters, and whole-candidate reviewers receive an acceptance-document reference and the slice's `### S<n>` section. Each row is indexed only by its test ID or NotTested owner and its covers; stimulus, expected, user-result and NotTested-reason prose stays in that nwdes-rendered document, which the role reads with its own file tool. The acceptance producer's existing full output contract is unchanged.
The whole-candidate review packet shares one acceptance-document pointer across its slice section/index blocks; per-slice recipes keep their own complete pointer.
The acceptance pointer declares the row columns once: `Rows: locator/owner, covers, obligations`. Every row retains its own complete covers list; it is never inherited from another row. Repeated test-ID prefixes print once as `Test prefix <prefix>:`; prepend that exact prefix to each indented suffix to recover the complete locator. Unindented test IDs and NotTested owners are complete values outside that prefix scope; row order is unchanged.
A row that binds obligation keys prints them after its covers as `obligations KEY,...`; a row without bound keys prints no such suffix.

nWave's internal reference suite compares baselines after replacing repository-root occurrences with `<root>`; the printed bundle itself stays unchanged. The suite reserves the declared maximum root-path bytes per occurrence when checking raw class ceilings. Ceilings, root-path allowance and per-reference baselines live in `tests/nwdes/support/budgets.py`; only the supplied candidate diff is excluded. Installed users get no size gate, refusal or budget step.

Slice recipes that bind promises print only the promises cited by that slice's public oracle. The optional charter recipe takes no slice: it covers the complete Feature and, like examiner bundles, retains the whole feature's public promises.

Role asks. Each recording role's bundle prints the asks its policy names, in policy order. For each asked member the bundle prints the policy sentence with its recording verb substituted, then `Accepted values:`, `Shape:` (the verb and its flags), `Example locator:`, a `Required:` line when the member's minimum is 1 or more, and `Owes <member>:` lines: one per code target for `reuse` and `impact`, and one `the design, once` line for `architectural_tests` and `contract_tests` once a slice has a code target. The `Required:` line names the policy member, for example `acceptance.covers`; the refusal names the record path, for example `acceptance.row.covers`.

The asks come from `src/nwdes/policy.toml` (see [design](design.md)). Records written before this version still read: the stored read path does not apply the policy, so an ask constrains only new role output.

Simple path/locator tokens may print bare; whitespace or Markdown-significant characters retain collision-safe code spans.

Native cooperation is the default for nWave roles, not an opt-in prompt mode. The caller supplies the artifact owner and current permitted peer contacts through `--root-context`. Roles use the harness's native messaging; nwdes provides no inbox, broker or transport. Communication does not transfer artifact ownership.

The existing root relay remains available only where native messaging is genuinely absent. Authentication failures, failed probes and unknown capability do not establish absence. Independent assessments retain their evidence boundary, and examiner input stays on the sealed public route.


| Option | Meaning |
|---|---|
| `--role` | Installed specialist role name |
| `--handoff` | Input handoff file |
| `--repo-root` | Repository root; defaults to the current checkout |
| `--jev` | Authorized or unauthorized; optional, and authorized by default when neither the flag nor a configuration tier declares `jev` (repository over global, default `~/.nwave/config.json`); the flag wins over configuration; printed in every bundle; nwdes itself never writes or persists it |
| `--baseline-failure ID OWNER` | Repeatable known baseline failure and owner; producer bundles only, never examiner or charter bundles |
| `--task` | discuss or charter for product owner; expectations or examine for examiner; omit for roles without tasks |
| `--slice` | Required, optional or rejected as listed below; omission selects no slice |
| `--phase` | before-move or after-move-before-behavior for crafter prefactoring; omission selects implementation |
| `--diff` | Review diff file; for embedded review use the complete slice change from its base commit, including approved oracle/support changes; for final review use the whole candidate change from the feature base; omitted means none |
| `--root-context` | Root-supplied text, printed verbatim; refused for examine |
| `--commit REV` | Required for both review recipes: resolves to the full SHA of clean lane HEAD; omitted for other recipes |

| Role | `--slice` admission | Task |
|---|---|---|
| nw-product-owner | Rejected for both tasks | discuss (default), charter |
| nw-solution-architect | Rejected | None |
| nw-user-examiner | Rejected for both tasks | expectations, examine |
| nw-acceptance-designer | Required | None |
| nw-acceptance-designer-reviewer | Required | None |
| nw-functional-software-crafter | Required for implementation and both prefactoring phases | None |
| nw-software-crafter | Required for implementation and both prefactoring phases | None |
| nw-software-crafter-reviewer | Optional: present for embedded slice review; omitted for final whole-candidate review | None |

Only review recipes admit a diff and require `--commit REV`. No prompt recipe admits `--observation` or `--observation-file`: these retired names, including `--name=value`, refuse with `SelfGatheredEvidence` before parsing, reading files or producing output. Abbreviations are unknown arguments. `examine.user-v1` also refuses `--root-context` before any read or workspace creation. Examination needs fixed expectations, not host evidence. The examiner gathers its own observations through `nwdes examine read` and `nwdes examine probe` in its public-only workspace, then records each through its generated examination verbs before citing it. The workspace projects committed public documents at candidate HEAD, not working-tree edits, and contains only `public/` and initially empty `scratch/`, outside candidate and main worktrees.

The expectations recipe prints the current fixed public rows with IDs, complete texts and promise mappings, or `None.` before the first set. The examiner records with the expectations CLI verbs and closes. A deliberate replacement closes with `--revise`. See [expectations](expectations.md).

Review bundles name the full reviewed commit and each touched path on its own line. Git resolves the requested revision. An oracle review bundle judges its slice's oracle and supports by content, so their uncommitted bytes are not dirty paths, and a crafter prompt for that slice refuses `OracleChanged` once those bytes differ from the approved ones. Only the selected feature's directory (its documents, drafts and `runs/` records) and git-ignored paths are exempt from evidence cleanliness. Unavailable git produces `InputUnreadable` naming the failed step.

The final reviewer owns selection and sufficiency of the touched-file selected tests at that commit. It reuses a complete applicable native result (host, CI or the normal commit hook) whose source, test, argv and runtime inputs are unchanged, citing its original operator and run; it executes only missing or affected checks, once. It records actual argv, exit, stdout and stderr of each run it executes with `nwdes review observation add --text` or `--text-file`, including empty selection, incomplete selection and no selector found. Reuse never waives a check. nwdes stamps observations; it never selects or runs tests. See [review](review.md) for stamps, close refusals and owner-addressed findings.

`review.craft-v1` admits `--slice` for embedded review: its packet carries that slice's declared commands for reference and its record uses `--subject slice --slice S<n>`. Without `--slice`, final review carries the declared commands of every slice for reference and records with `--subject candidate`. Reviewers receive the supplied diff, slice projections, declared commands and ADR names, not model internals or ADR bodies. Shared-record text remains in the named architecture document. The reviewer runs the touched-file selector and selected tests once, reusing applicable unchanged observations with their original provenance; declared-command live observations stay with the host. Missing, unrun or failing selected-test evidence is a finding. Final review is fresh and independent and does not consult embedded review records. Independent approval of each public oracle before craft stays, an artifact-quality check of that oracle alone with its observed semantic RED; no per-slice charter is produced.

The reviewer inspects every changed test, fixture and support outside the slice driving oracles. It rejects changes the authority does not necessitate or that reduce discrimination through changed expected values, softened fixtures, narrowed inputs, removed cases or skips, even when assertions remain syntactically strong. An authority-necessitated behaviour-preserving migration is not a finding; an expected value changed to match new output without authority is. Approved driving oracles and their supports still receive full oracle-quality review.

```text
nwdes prompt --role nw-user-examiner --task examine --handoff docs/feature/search/handoff.json
```

Refusals include MissingFact, HandoffInvalid, DanglingReference, InconsistentFacts, PlaceholderUnbound, FieldUnused, SelfGatheredEvidence, WorkspaceContaminated and InputUnreadable. Refusals print no bundle. Retired host flags and contaminated examination workspaces exit **2**; unavailable git or temporary-directory writes exit **1**.

An expectations bundle needs at least one product promise; oracle and oracle-review bundles need at least one promise cited by the slice's public oracle. Missing promises refuse with `MissingFact` before a bundle is constructed.

Give each recording role the complete prompt bundle. All recording roles use their kind's nwdes CLI verbs, record their values, and close. The root does not submit role output. See the [feature route](../deliver-feature.md) for lane-first ordering.
