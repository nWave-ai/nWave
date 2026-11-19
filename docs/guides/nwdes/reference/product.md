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

A feature holds at most five product slices. `nwdes product slice add` and `nwdes slice set` that creates the next slice refuse a sixth with `PartInvalid: product.slices`, naming the count held. The refusal records nothing and sends the reader to the way out: tell the human, propose the split into separate features of one epic as a proposal the human decides, and run `nwdes feature new --feature <new-feature> --epic <epic> --request '<outcome>' --size S --value '<value>'` once for each new feature. A handoff that already holds more than five slices still reads, prints and closes; only an added slice beyond five is refused.

## Human-authorised amendment of a promise

A published promise changes or retires only with a declared amendment. `nwdes product promise set --id P<n>` on a promise the published record already holds must carry `--amendment-authority TEXT` and `--amendment-reason TEXT` with its new text (or the other fields of a Scenario). `nwdes product promise remove` on a published promise must carry the same two flags, whether it selects the row by `--id P<n>` or by its one-based position `--at N` in the draft; the position is resolved to the row before the rule is applied. Without both, the verb is refused with `MissingFact: product.promises.P<n>.amendment`, names the two flags, and writes nothing. A promise added in the draft has no identity until close and takes no authority. This refusal is a change to existing commands: before it, a published promise could be changed or removed without a record. The owner decision to make the flags mandatory is recorded for confirmation.

A retirement stays visible. The examiner packet prints each retired promise under the promises, with its last text and its `Retired by` authority and reason, labelled as recorded. A slice cannot cite a retired promise afterwards. The replacement a human adds in the same draft (`promise add`, then a slice that cites its predicted id) needs no authority beyond the retirement's own.

What the rule does and does not establish: it makes a silent change or retirement of a published promise impossible through these verbs, and the examiner sees each one with the authority and the reason as recorded. It does not make an unauthorised change impossible: nwdes records the authority exactly as the person typed it and cannot verify who that person is, so the examiner sees a declared authority, not a verified one. Each later change states its own amendment; an earlier authority is never shown for a text it did not declare.

Not covered by this rule (open owner questions): slice observations, scope and decisions are not changed by this rule; the observation of a slice is shown to the examiner and may change without an amendment. Expectation rows are fixed once published; a row that cites a retired promise is withdrawn by the close and its withdrawal is reported on stdout, not in the examiner packet. Charter and public oracles are not guarded by this rule.


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
