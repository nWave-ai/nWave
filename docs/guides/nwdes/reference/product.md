# product

The product owner records with the `nwdes product` CLI verbs and closes. See [role recording](index.md#role-recording).

The record holds product promises, scope, decisions, journey, and slice intents. Closing replaces the product part and renders outputs; it does not restore omitted rows. Seed a draft from the current record to retain rows during an update.

## Slice promise coverage

`nwdes product slice add` and `slice set` require repeatable `--promise P<n>` references to promises carried by this draft. Slice rows retain these references in `promises`, the existing coverage representation. Missing or unknown references refuse before writing the draft, with WHAT/WHY/HOW guidance to cite an existing promise, add a justified Request promise with `nwdes product promise add`, or start a separate `nwdes feature new`.

Promise IDs resolve exactly as at close: published promises with matching words retain their IDs; new promises take the next published counter. Preview reuses publication's content matching and coalescing without issuing identities or interning text before refusal checks finish. Removed published IDs are not recycled. In a first unpublished draft, numbering reflects the promises that remain after removals. A fresh draft over a published product can cite only the promises it carries, not omitted published rows.

Draft edits consume the inspected previous units they actually need, not a whole-handoff acceptance gate. An unrelated malformed previous work value does not suppress authoring or later independent product diagnostics; close still reports all runnable defects before publication.

Product close requires every slice to cite existing promises and every Request promise to be covered by a slice. Older handoffs without slice links remain readable and round-trip unchanged; revising and closing their product requires complete coverage. No slice-size or dependency-connectivity restriction is added.
Product close also requires a scope-out line: record it with `nwdes product scope-out add --text TEXT`. Where nothing is excluded, write a line such as `Nothing excluded because X`. A close without one refuses with MissingFact naming `product.scope_out`; handoffs published before this rule still read.

Check the split before closing: does every slice contribute to this one value, or did you bundle unrelated outcomes? Do not answer yes by default. Split unrelated outcomes into a separate nwdes feature new.


## Replacement and withdrawal

A valid replacement retires previously present identities absent from the candidate product. Existing identity rules still apply: carry an existing ID for the same record; unchanged content can retain its ID; unmatched content receives a new ID. There is no positional or semantic aliasing.

| Retired identity | Withdrawn dependent entry |
|---|---|
| P ID | Each citing `public_oracle` record and expectation row |
| S ID | That slice's keyed design and acceptance list |
| E ID owned by a withdrawn expectation row | Its examination verdict |

The Feature charter is never withdrawn: it covers the complete Feature, not any slice. Withdrawal repeats through dependent identities. Each affected structured entry is removed whole, not repaired by stripping or rewriting citations. Unaffected entries retain their IDs, content, and relative order. Removing a parent reports that parent once, not each child. An empty expectation set remains present and requires a deliberate expectations revision.

Invalid replacement input, missing or unknown slice promise links, uncovered Request promises, conflicting identities, and forbidden transitions refuse without writing. Retirement of an existing identity alone is not a `DanglingReference` refusal, but a retained slice cannot cite a retired promise. See [standard withdrawal results](index.md#standard-results) for reporting and role-specific repair guidance. Retained IDs do not certify semantic freshness; the root alone chooses additional review or examination.


Returns written or unchanged paths. Refusals: MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid, RoleNotAccepted, DanglingReference, UncoveredPromise. The host invokes the product owner; this command does not.
