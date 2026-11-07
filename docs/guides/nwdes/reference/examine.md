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

`probe` admits only the public commands of the candidate's declared kind, read from its committed manifest. Arguments and `--option=value` values must be relative and resolve inside W from `W/scratch`; escapes, including symlink escapes, produce `ProbeRefused`, exit 2, naming the admitted commands. For a Python package (committed `pyproject.toml`, commands from `[project.scripts]`), an admitted command runs through the current Python interpreter with `-I -B`, no shell or project runner, and candidate import roots derived from the committed wheel package declarations. For a Rust binary (committed `Cargo.toml` with `[package.metadata.nwdes]` and `kind = "rust-binary"`; commands are the `[[bin]]` names, or the package name when there are none), an admitted command runs the built executable at `target/release/NAME` directly, with no interpreter and no toolchain. That executable is a build output, not a committed file: it must be a regular file with its executable bit. The check follows no symlink and opens each name of the path relative to the directory before it; the probe starts the very file it checked, through its descriptor, so a later replacement of the path cannot change what runs. Each cause has its own refusal, all `InputUnreadable` naming the path, and each names its own remedy: a symlinked file (remove the symlink, then build), a symlinked directory on the path (remove that symlink, then build, which creates real directories), a path component that is a regular file (remove it, then build), a directory the user cannot search (give search permission), a missing or non-executable file (remove what is there, `cargo clean`, then build, or build elsewhere with `CARGO_TARGET_DIR` and copy), a name the file system cannot hold (shorten it), and a launch the system refuses, by its cause: a file system mounted noexec (`EACCES` or `EPERM`: copy the checkout with `cp -a` to a filesystem mounted with exec, build the copy, and examine it), a file that is not a program (`ENOEXEC`: remove it, then build), and any other error, which the examiner names as having nothing to run. Every remedy named in a refusal is executed by a test against real `cargo build --release` where it names cargo. A file the system cannot start is refused by the same name. Protection depends on the platform. Where the platform opens names relative to a directory descriptor without following symlinks (Linux, macOS), the check pins the file the probe starts through its descriptor. Elsewhere (Windows, or any platform without that support), each component of the declared path is checked with `lstat`, a symbolic link or reparse point is refused, and the executable is started by its path: a replacement of the file between the check and the start is not detected there. The Rust kind names the built file `target/release/NAME` on Linux and `target/release/NAME.exe` on Windows; a declared name already given with `.exe` is taken as it is. Accepted limits, decided by the owner: on a platform without descriptor-relative opens, a replacement of a checked path component between the check and the start is not detected, so the probe is not a sandbox there; Python byte identity rests on the characterisation tests and the unchanged code path, not on every possible input. An execute-only native executable (mode `0111`) is accepted and run, because the check needs search permission on the directories and no read permission on the file, where the platform provides `O_PATH` (Linux). An execute-only script is not run: its interpreter must read it, as a shell would refuse it. On a platform without `O_PATH` (macOS) an execute-only executable is checked by the `lstat` walk, which needs search permission on the directories only, and is started by its path: the replacement limit of that walk applies to it. A directory the user cannot search is refused with the search-permission remedy, which the test executes. The descriptor pins the file's inode: it is not a sandbox, it does not protect bytes rewritten in place before the start, and it does not constrain what the declared program does once it runs. A committed `pyproject.toml` decides the kind as it always has, so Rust metadata beside it is ignored. A candidate with no readable declaration is refused with `InputUnreadable` naming each supported declaration. The workspace shows the prose under the documentation roots (`.md` and `.tmpl` files), as for every candidate; source files are not shown, but prose placed under those roots is, by design. Missing third-party imports remain the command's public failure. Its cwd, HOME and TMPDIR are scratch; only PATH and LANG are copied from the invoking process, with LANG defaulting to C.UTF-8. The command's exit and both byte streams pass through, replacing every candidate checkout path with `<candidate>`.

Every read and probe rechecks the committed public projection, refusing `WorkspaceContaminated` when names, kinds or bytes differ, a public entry is writable, or the workspace is inside either checkout. Top level must contain exactly real `public` and `scratch` directories. The public projection admits no symlink; scratch may hold arbitrary examiner entries, including symlinks, and workspace inspection never follows them. Probe argument resolution still refuses escapes through scratch symlinks. Projection reads use the optional git port with ambient GIT_* variables removed; unavailable git yields `InputUnreadable`, exit 1. The workspace and bundle contain no checkout location. These boundaries do not confine the examiner's own Bash process or paths an admitted program computes internally.

## Workspace removal

nwdes removes the examination workspace after `nwdes examine close` succeeds: every workspace its prompts recorded in this checkout, each named in the close output. A refused close removes nothing and keeps the workspace for the retry; a workspace whose top level is not exactly `public` and `scratch`, or that differs from the committed projection, is kept and named as kept. A close run from a worktree other than the one that built the prompt removes nothing and says so. The examiner deletes only the files and directories it created outside its workspace for this examination, and nothing else. It never deletes the candidate checkout, nwdes records or any path it did not create, and it names in its final message any trace it could not remove. Evidence remains in the recorded observations and verdicts.

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
