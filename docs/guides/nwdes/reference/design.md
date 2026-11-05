# design

The architect records with `nwdes design` verbs through the CLI and closes. See [role recording](index.md#role-recording).

The record holds the paradigm, shared records, slice designs, and ADR declarations. Closing replaces that part, assigns identities, and renders outputs. nwdes computes new ADR numbers; do not invent keys.

A close refuses with MissingFact until each code target of a slice has a `reuse` decision and an `impact` decision, each covered by a row of its analysis or by a reasoned `not-applicable` (`nwdes design not-applicable add --in SLICE --analysis ANALYSIS --reason TEXT`). The design also needs an `agreement` row or a reasoned not-applicable, and `architectural_tests` and `contract_tests` rows or a reasoned not-applicable of each, once any slice has a code target. Prose targets owe nothing. A record scope holds either rows of an analysis or its not-applicable, never both. A blank reason refuses with PartInvalid at the row's `records.not_applicable[N].reason` path.

A code-target slice owes one `prefactoring` decision: a `prefactoring` declaration in that slice (`nwdes design prefactoring set --in SLICE --move TEXT --preserved TEXT --existing-oracle PATH --verification COMMAND`) or a reasoned `not-applicable` of `prefactoring` (slice or shared). A slice holding both is refused with PartInvalid. A move names the follow-up change it makes easier; any level L1 to L6 is allowed. Prose-only slices owe nothing.

Recording verbs. Reuse and impact rows take `--in SLICE` or `--shared`; a row in either scope whose locator names a code target covers that target. Agreement and design-level test rows take `--shared` or `--in SLICE`; both scopes satisfy the design-level rule. An agreement row names one party to a shared contract the change touches, `Producer` or `Consumer`, with its locator, a closed decision and a reason. `Incompatible` is accepted and rendered into the design document.

| Analysis | Verb | Required flags |
|---|---|---|
| `reuse` | `nwdes design reuse add --shared` or `--in SLICE` | `--symbol NAME --locator PATH:LINE --decision Reuse\|Extend\|Replace\|CreateNew --reason TEXT` |
| `impact` | `nwdes design impact add --shared` or `--in SLICE` | `--kind TEXT --locator PATH:LINE --decision Changed\|Migrated\|UnchangedCompatible --reason TEXT` |
| `agreement` | `nwdes design agreement add --shared` or `--in SLICE` | `--contract LINE --locator PATH:LINE --party Producer\|Consumer --decision Migrated\|UnchangedCompatible\|Incompatible --reason TEXT` |
| `architectural_tests` | `nwdes design architectural-test add --shared` or `--in SLICE` | `--obligation TEXT --oracle PATH --command COMMAND` |
| `contract_tests` | `nwdes design contract-test add --shared` or `--in SLICE` | `--obligation TEXT --contract LINE --producer LINE --consumer LINE --observation TEXT --oracle PATH --command COMMAND` |
| `prefactoring` | `nwdes design prefactoring set --in SLICE` (one per slice, no `--shared`) | `--move TEXT --preserved TEXT --existing-oracle PATH --verification COMMAND` |

A reasoned not-applicable is `nwdes design not-applicable add --in SLICE --analysis ANALYSIS --reason TEXT`. `ANALYSIS` is one of `reuse`, `impact`, `agreement`, `architectural_tests`, `contract_tests`, `prefactoring`; any other value is refused with PartInvalid by argument parsing.

A reuse row's locator and symbol must resolve: the file exists under the repository root, the line lies within it and the symbol occurs in it. Otherwise the close refuses with PartInvalid naming the row, for example `PartInvalid: design.slices.S1.records.reuse[2]`. A `CreateNew` row and an impact row are not resolved.

The refusal tokens for missing decisions are `MissingFact: design.slices.<S> target <path> has no reuse decision` (or `impact`), `MissingFact: design has no agreement record`, `MissingFact: design has no architectural_tests record` (or `contract_tests`), and `MissingFact: design.slices.<S> targets <paths> have no prefactoring decision`.

The asks that the role prompt prints come from `src/nwdes/policy.toml`: one `[member.NAME]` entry per asked member, and `[role.NAME]` lists each role's asks. Coverage is enforced by `_design_obligations` in `src/nwdes/handoff.py`. An ask for an analysis the record already names is a policy edit only. A new analysis name needs a shape edit in `src/nwdes/handoff.py`: a value in the `not_applicable` analysis enum and a `RECORDS` member, plus an entry in the `names` map in `src/nwdes/drafts.py` whose value is the singular hyphenated verb.

Shared decisions and constraints carry an assigned D or K ID, their text and the existing slice IDs they govern. Retained rows cite their ID even when text changes; new rows omit it and receive the next never-reused ID. Unknown IDs refuse. Slice bundles include only their own records and governing shared decisions/constraints, not the whole shared design.

The handoff writer uses standard JSON serialization with sorted keys, zero indentation (`indent=0`), literal Unicode and one trailing newline. Members remain line-oriented for readable diffs. Older JSON layouts remain readable and are rewritten in this standard layout on the next write; do not reformat the handoff by hand.

Writing checks every slice verification and prefactoring command's first shlex word in the writer's environment. Bare programs resolve on invoking PATH; relative paths are confined lexically under the repository root, without following symlinks for confinement, and absolute files may be elsewhere. Existing symlinked files/directories resolve, dangling links and relative `..` escapes do not. All unresolved commands are reported together with `PartInvalid`; commands are not executed.

A design slice whose targets are all prose assets (see [slice](slice.md#prose-only-slices)) closes without an oracle, verification, supports, prefactoring or public stimulus, expected and falsifier. Its public oracle keeps only its promise references. Closing records its acceptance row as `NotTested` with reason `prose, verified by EXAMINE`, so the acceptance designer is not asked to write one. A design slice with any non-prose target keeps its oracle and verification required; supplying an oracle field on a prose-only slice refuses with `OracleOnProse`, naming each supplied field.

Distinct ADR body slots may not repeat normalized whitespace-equivalent text when at least one row is new or changed. A slot is `(existing ADR key, field)` or `(new row position, field)` for context, decision, alternatives and consequences. Identical repeated operations on the same existing slot are legal; cross-key, cross-field and new-row copies refuse with `InconsistentFacts`, naming both slots. Unchanged retained legacy rows are not compared with each other, and an unproduced field does not prove a change. Stored text is never rewritten.

Use [delta](delta.md) to inspect changes. Run a separate design review only when a shared decision or ADR changes; otherwise the whole-candidate review is the review. Default budgets need no statement or measurement in the design; timing evidence is due only at half a test's budget or on a derogation request.

An assigned record ID belongs only to the list and retained parent that issued it. Seed a draft from the current record to retain it. Add new records through the kind verbs; nwdes assigns their IDs.

A model has no own ID. Its prior parent is matched by complete expanded content, not path alone: IDs are ignored, absent or empty optional values are normalized, and list order is content. A change to property statements, atoms, assumptions, mutants or other model content loses that parent match. Preserve the complete previous model content to retain its nested mutant IDs. Do not edit the handoff by hand.

On rework, retain each previously declared ADR that the current repository register still marks Accepted: declare its `key` with its unchanged body, or replace it explicitly with `supersedes` naming that key and an Accepted successor. Omitting `adrs`, supplying an empty array, or adding an independent decision does not explain removing an accepted declaration. An ADR already superseded elsewhere need not be retained.

A selectorless row with the same exact title but a different body from an accepted ADR in the same allocation prefix refuses; a title never establishes identity or supersession. For an independent decision use a distinct title. Equal-body selectorless replay may reuse an existing identity. Explicit supersession emits the successor before updating the predecessor; replay reuses the successor.

## Replacement and withdrawal

A valid replacement retires existing design identities absent from the candidate. Carry existing IDs for same-record edits; otherwise existing content-matching and identity-assignment rules apply. B2 and B3 replaced by B4 are retired identities, not aliases of B4: no dependent evidence transfers to B4.

Each acceptance row citing a retired design identity is withdrawn whole. Multiple retired citations in one row produce one notice listing every cause. An unaffected row retains its ID, content, and relative order. A notice uses the row's original, pre-replacement index.

Expectations cite product P IDs, not design identities, so design replacement alone does not withdraw expectations or their verdicts. Design replacement leaves the Feature charter unchanged. Invalid input, unknown newly supplied references, conflicting IDs, and forbidden ADR transitions still refuse without writing.

Repair guidance names `nw-acceptance-designer` for affected slices. Give that role a fresh prompt so it can record replacement rows and close. Guidance does not invoke the role. See [standard results](index.md#standard-results).

Returns written or unchanged paths. Refusals include MissingFact, OracleOnProse, PartInvalid, InconsistentFacts, ConfigurationMalformed, HandoffInvalid, RoleNotAccepted, DanglingReference, AdrDeclarationDropped, AdrSelectorRequired, AdrAcceptedImmutable, AdrTransitionInvalid, AdrForeignLayout and AdrKeyClash. ADR and program refusals occur before any output is written. Return a refusal to the architect; the root does not submit role output.
