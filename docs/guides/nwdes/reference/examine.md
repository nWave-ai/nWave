# examine

The examiner records with the `nwdes examine` CLI verbs and closes. See [role recording](index.md#role-recording).

The examiner records its observations, then sets a verdict for every current E ID: met, or unmet with class oracle_gap, product_violation, expectation_defect, or observation_gap. Each verdict cites at least one recorded observation. Closing stores the cited text with the verdicts and renders the acceptance brief. nwdes does not judge the evidence.

The lean route invokes the examiner after whole-candidate review, without host observations or root context. Pass its complete bundle inline. The examiner gathers its own observations in the named public-only workspace, records each through its generated examination recording verbs before citing it, and judges from the user's point of view. Source, diffs, private plans and producer judgments do not belong in its packet. There is no per-slice charter step and the root submits no reply file.

A record can contain unmet expectations; a successful close alone is not a successful public examination. Resolve unmet expectations before integrating the same reviewed candidate. Each finding a rework repairs becomes an oracle test, observed RED and then GREEN, as the rework bundles state.

## Gathering public evidence

The bundle's TASK section sets the wall budget and the probing rules. The budget is a recipe instruction; nwdes enforces no time limit.

Run these verbs from the candidate checkout top level, using the workspace named in the bundle:

```sh
nwdes examine read --workspace W
nwdes examine read --workspace W docs/guides
nwdes examine probe --workspace W -- nwdes --help
```

`read` lists a directory or prints a regular file relative to `W/public`. It refuses paths outside that projection or through a symlink with `ReadRefused`, exit 2.

`probe` admits only console scripts declared in the candidate's committed `pyproject.toml`. Arguments and `--option=value` values must be relative and resolve inside W from `W/scratch`; escapes, including symlink escapes, produce `ProbeRefused`, exit 2, naming the admitted commands. An admitted command runs through the current Python interpreter with `-I -B`, no shell or project runner, and candidate import roots derived from the committed wheel package declarations. Missing third-party imports remain the command's public failure. Its cwd, HOME and TMPDIR are scratch; only PATH and LANG are copied from the invoking process, with LANG defaulting to C.UTF-8. The command's exit and both byte streams pass through, replacing every candidate checkout path with `<candidate>`.

Every read and probe rechecks the committed public projection, refusing `WorkspaceContaminated` when names, kinds or bytes differ, a public entry is writable, or the workspace is inside either checkout. Top level must contain exactly real `public` and `scratch` directories. The public projection admits no symlink; scratch may hold arbitrary examiner entries, including symlinks, and workspace inspection never follows them. Probe argument resolution still refuses escapes through scratch symlinks. Projection reads use the optional git port with ambient GIT_* variables removed; unavailable git yields `InputUnreadable`, exit 1. The workspace and bundle contain no checkout location. These boundaries do not confine the examiner's own Bash process or paths an admitted program computes internally.

## Workspace removal

The examiner deletes its workspace only after `nwdes examine close` succeeds; a refused close keeps the workspace for the retry. After that success it deletes the workspace named in its bundle and every file or directory it created outside that workspace for this examination, and nothing else. It never deletes the candidate checkout, nwdes records or any path it did not create, and it names in its final message any trace it could not remove. Evidence remains in the recorded observations and verdicts. nwdes does not remove the workspace; removal is the examiner's own shell action, and a producer-side removal is a separate follow-up Request.

## Scratch and fixtures

Fixtures go in the bounded scratch under the examination workspace. Avoid RAM-backed file systems for large scratch.

## Recording and citing observations

Use the scope flags from the generated verb reference on each recording command:

```sh
nwdes examine observation add --feature greeting --text "The public greeting names the visitor."
nwdes examine verdict set --feature greeting --expectation E1 --verdict met --observation O1
nwdes examine close --feature greeting --outcome accepted --diagnostic "Every expectation is judged from public observations."
```

`observation add` prints its nwdes-issued O ID; use that printed ID, not an invented identifier. `--observation` is repeatable, so a verdict can cite several observations and several verdicts can cite the same observation. `--text-file PATH` reads literal UTF-8 instead of inline `--text`. Observation text, including empty file contents, CRLF, trailing newlines and backticks, is preserved exactly in the published facts and fenced acceptance text.

`observation set --id O1 --text TEXT` replaces the text without changing its ID; `--at N` selects the same row by its 1-based position. `observation remove` accepts either selector and leaves any citations in place: close refuses a dangling citation rather than silently changing the judgment. Removed IDs are not reused within the draft.

A verdict without a citation is refused with `UncitedVerdict`. Close checks every current E ID together and refuses missing verdicts with `PartInvalid` or citations to unrecorded observations with `DanglingReference`. Refusals retain the draft and name the record-and-cite remedy; nothing is published until the whole examination is valid.

`open --from-current` reconstructs observations from the published cited text in first-citation order over E IDs in numeric order, coalescing identical texts. These draft-local O IDs are issued afresh; the published handoff stores interned text references, not O IDs. Examinations published before citations existed still decode and render, but closing a new examination requires citations.


## Verdict preservation and withdrawal

Verdicts are keyed by E IDs. An expectations revision that omits E2 withdraws only `examination.E2`. Product retirement can withdraw an expectation row and cascade to its verdict. The verdict notice's WHY names the original row, such as `expectations.rows[1] (E2) was withdrawn.`, not merely the retired product promise. Unrelated acceptance changes do not clear examination.

Remaining verdicts are preserved, but a partial examination is not complete. Upstream replacement does not print a new `accepted` result. `examine close` requires the entire current E-key set.

After an expectations revision, the root can give a fresh examination prompt to the examiner. The examiner records the verdicts and closes. Notices supply guidance only, not automatic invocation. Retained IDs do not prove that evidence is current.


Returns written or unchanged paths. Refusals: MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid, RoleNotAccepted, DanglingReference, UncitedVerdict. Resolve unmet expectations before declaring delivery complete.
