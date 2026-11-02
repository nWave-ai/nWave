# slice

`slice set` writes the product intent and design facts for a minimal-route slice. It uses the [common write options](index.md#common-write-options).

| Option | Value or omission |
|---|---|
| `--slice` | Existing S ID to update; omit to create the next slice |
| `--observation` | User-visible slice result |
| `--paradigm` | functional, object_oriented, procedural; required for the first design, otherwise reuses it |
| `--oracle` | Acceptance oracle path; required on creation unless every target is a prose asset, then forbidden |
| `--stimulus` | Public stimulus; required on creation with the oracle unless every target is a prose asset, then forbidden |
| `--expected` | Expected public result; same rule as `--stimulus` |
| `--falsifier` | Observation that disproves success; same rule as `--stimulus` |
| `--command` | Whole ordered single-line verification command list; required on creation unless every target is a prose asset, then forbidden; omission keeps it on update; the first shlex word must resolve at write time |
| `--support` | Whole ordered support list; omission keeps it on update, or uses none on creation; forbidden when every target is a prose asset |
| `--create` | Whole ordered Create-target list; omission preserves that change-kind list on update |
| `--extend` | Whole ordered Extend-target list; omission preserves that change-kind list on update |
| `--promise` | Whole ordered list of slice-owned promises; omission preserves prior own promises and oracle references |
| `--cites` | Whole ordered list of other promise IDs; omission preserves prior non-own citations; supplied values replace them |
| `--decision` | Whole list of governing shared D IDs; repeatable; omission preserves membership |
| `--constraint` | Whole list of governing shared K IDs; repeatable; omission preserves membership |

Returns written output paths. Own promises precede other citations. Refusals: MissingFact, OracleOnProse, PartInvalid, ConfigurationMalformed, HandoffInvalid, DanglingReference. Verification commands are stored, not run.

The product slice's `promises` are the same owned-then-cited IDs as its resulting public oracle. A new slice requires at least one owned promise (`--promise TEXT`) or existing citation (`--cites P<n>`); neither is inferred. Missing coverage refuses before publication: cite a Request promise, add a justified promise, or move an unrelated outcome to a separate `nwdes feature new`. Updates synchronize product links when oracle promises are available. Updating a historical slice without oracle promises does not retrofit its links or impose a global product-close coverage check; explicit `nwdes product close` remains strict.


The root writes a bugfix slice with its public promise before examiner expectations. A lane is optional: use one in an isolated checkout or for a known bugfix, run from the chosen checkout top, and let roots default to the current directory; explicit roots are optional overrides. Use one slice by default when one behaviour suffices. Each slice oracle gets one independent acceptance-test review before craft; no per-slice charter is produced. An embedded refinement review of a GREEN slice is optional; when used it is recorded with `--subject slice --slice S<n>`. After all slices are GREEN, a fresh independent reviewer performs the required final whole-candidate review with `--subject candidate`; one source-blind EXAMINE judges the complete Feature.

Program resolution uses the invoking PATH for bare words. A path word must be an existing absolute file or a lexically root-confined relative file; symlinked files/directories are allowed, but dangling links and relative `..` escapes refuse. All unresolved verification/prefactoring programs are reported in one refusal. This write-time check does not establish that later arguments are valid or that the program remains available when verification runs.

## Prose-only slices

A slice is prose-only when every `--create` and `--extend` target is a prose asset: a file under `docs/guides`, `nWave/skills`, `nWave/templates` or `nWave/agents` whose suffix is `.md` or `.tmpl`. Classification reads the normalised target path, never a flag. Absolute paths, paths that escape their root and other casings of a suffix are not prose. A slice with no target, or with any non-prose target, is not prose-only and keeps its oracle fields required.

A prose-only slice forbids `--oracle`, `--stimulus`, `--expected`, `--falsifier`, `--command` and `--support`. Supplying any of them refuses with `OracleOnProse`, naming each supplied field, and writes nothing. Keep its targets and `--promise` or `--cites` references. nwdes records one acceptance row for it: disposition `NotTested`, reason `prose, verified by EXAMINE`, owner `EXAMINE`, covering the slice's promises. EXAMINE and the whole-candidate review verify the prose; no test pins its wording.

Updating an oracle-bearing slice so that its targets are all prose withdraws its retained oracle fields with a `WITHDRAWN` notice and replaces its acceptance row with the `NotTested` row. A slice whose targets stop being all prose loses that row.

## Candidate and retirement

`slice set` validates references against the final composite candidate: the updated product slice and its owned promises, the replacement slice design, and retained records for other slices. It does not reject a reference solely because the old intermediate state would lack it.

A slice's own promises are the promises its public oracle cites that no other slice's public oracle cites and that this invocation does not name in `--cites`; a promise cited by the public oracles of two slices is shared and is no slice's own promise. An explicit `--promise` list is the whole ordered list of this slice's own promises: on an existing slice the k-th value replaces the text of the k-th own promise and keeps its P ID, so expectations, acceptance rows and verdicts citing it stay; extra values add promises at the next P IDs; own promises beyond the list are removed from the product promises, which retires their P IDs. `slice set` never replaces or retires a shared promise: a value given when no own promise is left to replace adds a new promise, and the slice keeps citing the shared one unless a supplied `--cites` list omits it. Omission of either option preserves the respective values described above.

When own promises beyond the `--promise` list are removed and their P IDs retire, apply the same withdrawal closure as [product replacement](product.md#replacement-and-withdrawal): remove whole citing public-oracle records and expectation rows, then verdicts belonging to withdrawn E IDs. This includes dependencies outside the updated slice. Keep unaffected entries unchanged; do not transfer evidence to replacement promises. Charter scope is the complete Feature, never an individual slice; slice changes and retirement leave the charter and any legacy historical labels unchanged.

Replacement and withdrawal are computed from that final candidate before writing. Invalid supplied facts or unknown references still refuse without writing. Equal observation text never coalesces slices or moves evidence: give S2 a distinct observation or update S1 with `--slice S1`.

For example, S1 initially cites its own P1 (`original`). S2 has P2 (`second`), then also cites P1 through `--cites P1`. P1 is now shared, so neither slice owns it. With those existing IDs in feature `shared`, run:

```sh
nwdes slice set --feature shared --slice S1 --promise 'revised'
```

Run from the project checkout's top level. S1 has no own promise left to replace, so the command keeps P1 as `original` and P2 as `second`, adds P3 as `revised`, and gives S1's public oracle `[P3, P1]`. S2 keeps `[P2, P1]`. No ID retires and nothing is withdrawn; stdout contains no `WITHDRAWN` line.


See the verified slice in the [tutorial](../../tutorial-nwdes-first-feature/).
