# charter

The product owner records the complete Feature's optional charter with the `nwdes charter` CLI verbs and closes. Charter prompts and verbs reject `--slice`. See [role recording](index.md#role-recording).

The record contains intent, exploration, at least one positive observation, and a negative observation. Build `nwdes prompt --role nw-product-owner --task charter` from the Feature's value, public promises, journey and every slice's observation and public start recipe. A fresh product owner supplies these values. Closing stores one Feature charter, replaces any prior charter and renders outputs.

The feature-charter prompt checks each slice independently before rendering. A damaged observation in one slice does not hide a missing design for another; all runnable defects appear in one refusal and no bundle is built.

The charter has no typed product-promise or design-fact citations. Slice changes and retirement leave it unchanged; preservation does not certify semantic freshness.

Version-3 handoffs remain readable: one legacy slice charter lifts to the Feature charter; several lift losslessly to `LegacySlices` and render in separately labelled legacy blocks. Their S labels are historical, not live slice references. Examination refuses those legacy blocks together, naming every label. Obtain a replacement through the charter prompt and `nwdes charter close`, never hand-edit the handoff.

Malformed version-3 charter entries are refused together at their persisted `charters.<key>.<field>` paths before lifting. Independent defects in the other handoff parts remain in the same refusal; no partial charter is lifted.

Returns written or unchanged paths. Refusals: MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid, RoleNotAccepted, DanglingReference.
