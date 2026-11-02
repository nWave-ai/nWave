# design

The architect records with `nwdes design` verbs through the CLI and closes. See [role recording](index.md#role-recording).

The record holds the paradigm, shared records, slice designs, and ADR declarations. Closing replaces that part, assigns identities, and renders outputs. nwdes computes new ADR numbers; do not invent keys.

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
