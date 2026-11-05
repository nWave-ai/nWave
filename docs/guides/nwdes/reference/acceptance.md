# acceptance

The acceptance designer records with `nwdes acceptance` verbs through the CLI and closes. See [role recording](index.md#role-recording).

The record contains rows with stimulus, expected result, user result, coverage references, and Tested or NotTested disposition. Closing replaces that slice's rows and renders outputs. It does not run tests or judge coverage quality.
Every row cites the promises it covers with repeatable `--covers P<n>`. A row without covers refuses at `acceptance row add` with MissingFact naming `acceptance.row.covers`. Each design law or architectural or contract test the slice owes is one obligation key, listed in the author bundle: a key the slice owns with its case text, and a shared key by id alone, its text in the architecture brief. A Tested row binds keys with `--obligation KEY`; a close that leaves an owed key unbound refuses with OpenObligation, one block per open key.

A Tested disposition contains its test locator and `still_passes_if` text, recorded with `--still-passes-if` or `--still-passes-if-file`. For each test, name the nearest plausible wrong behaviour it would still accept, and tighten the test when that behaviour violates its promise. An accepted close refuses every Tested row without a nonblank statement in one pass, retaining the draft. NotTested is not a waiver: a row without a pytest test still needs its assigned host observation or semantic assessment, and the absence of a test does not remove that obligation. NotTested rows need no `still_passes_if` statement. Legacy published Tested rows without one still read and render; reopening them requires a statement before publishing again.

In the lean route, the root fixes public promises and examiner expectations first, then invokes the acceptance designer per slice. There is no separate oracle review beyond the independent approval of each public oracle before craft, an artifact-quality check of that oracle alone; no per-slice charter. The host's live observations cover each slice's declared commands, with complete native argv, exit status, stdout and stderr. The final whole-candidate reviewer runs the touched-file selector and selected tests once on the assembled candidate, reusing applicable unchanged observations with their original provenance; affected checks remain required, and a changed candidate needs new observations. The root does not repeat the host's declared-command observations. Missing, unrun or failing evidence is a finding. Reviewers read only the packet, its exact named evidence locators and installed skills, without discovery or candidate edits. Their Bash scope permits only authorized Jev and all exact generated scoped `nwdes review` verbs, including open, abort and close; recording and closing remain mandatory even when Jev is unauthorized.

## Upstream replacement

A valid design replacement withdraws each whole acceptance row citing a retired identity; it never strips a citation while retaining the evidence assertion or transfers evidence to a replacement identity. Rows without retired references retain their identities, content, and relative order. Retiring the product S key withdraws the entire `acceptance.S1` entry once, rather than reporting its rows separately.

For replacement rows, give the acceptance designer a fresh prompt against the current handoff. The designer records the rows and closes. The root does not submit a reply file.

Guidance does not dispatch that role. Newly supplied unknown coverage references still refuse with `DanglingReference`; upstream retirement is instead reported through [withdrawal notices](index.md#standard-results).


Returns written or unchanged paths. Refusals: MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid, RoleNotAccepted, DanglingReference. See the fixture example in the [tutorial](../../tutorial-nwdes-first-feature/).
