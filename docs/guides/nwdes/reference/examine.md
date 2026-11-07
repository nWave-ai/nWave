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

`probe` admits only the public commands its candidate declares. A committed `pyproject.toml` with `[project.scripts]` decides first, as it always has, and a declaration beside it is ignored: an admitted Python command runs through the current Python interpreter with `-I -B`, no shell or project runner, and candidate import roots derived from the committed wheel package declarations. Every other candidate declares its commands in `.nwave/examine.json`, described in [Declaring public commands](#declaring-public-commands). A declared command runs its built file directly, with no interpreter and no toolchain. Arguments and `--option=value` values must be relative and resolve inside W from `W/scratch`; escapes, including symlink escapes, produce `ProbeRefused`, exit 2, naming the admitted commands.

The declared file is a build output, not a committed file: it must be a regular file with its executable bit. The check follows no symlink and opens each name of the path relative to the directory before it; the probe starts the very file it checked, through its descriptor, so a later replacement of the path cannot change what runs. Each cause has its own refusal, all `InputUnreadable` naming the path, and each refusal names its own remedy: a symlinked file (remove the symlink, then build), a symlinked directory on the path (remove that symlink, then build), a path component that is a regular file (remove it, then build), a directory the user cannot search (give search permission), a missing file (run the build the declaration names, so that the path becomes a regular file), a file without its executable bit (`chmod +x PATH`), and a name the file system cannot hold (shorten it). A launch the system refuses is named by its cause: a file system mounted noexec (`EACCES` or `EPERM`), a file that is not a program (`ENOEXEC`), and any other error, which the examiner names as having nothing to run. A file the system cannot start is refused by the same name.

Protection depends on the platform, and the examiner never checks a path by name and then runs it by name. It opens each name of the declared path relative to a directory descriptor without following symbolic links, then runs the very file it opened through that descriptor. Where the platform cannot open names this way (Windows, and any platform without descriptor-relative no-follow opens), every declared executable is refused with `InputUnreadable` naming the path, cause `no_descriptor_walk`, and a remedy: examine the candidate on a platform that has them. The declared path is used exactly as written; no suffix such as `.exe` is added.

Accepted limits, decided by the owner: the descriptor pins the file's inode. It is not a sandbox, it does not protect bytes rewritten in place before the start, and it does not constrain what the declared program does once it runs. Python byte identity rests on the characterisation tests and the unchanged code path, not on every possible input. An execute-only native executable (mode `0111`) is accepted and run where the platform provides `O_PATH` (Linux). Without `O_PATH` (for example macOS) the descriptor open needs read permission on each directory and on the file, so such a file or directory is refused with `not_readable` and a remedy that grants read permission. An execute-only script is not run: its interpreter must read it, as a shell would refuse it. Windows was not run for this contract; declared executables are refused there by design.

A candidate with no readable declaration is refused with `InputUnreadable` naming the declaration file. The workspace shows the prose under the documentation roots (`.md` and `.tmpl` files), as for every candidate; source files are not shown, but prose placed under those roots is, by design. Missing third-party imports remain the command's public failure. Its cwd, HOME and TMPDIR are scratch; only PATH and LANG are copied from the invoking process, with LANG defaulting to C.UTF-8. The command's exit and both byte streams pass through, replacing every candidate checkout path with `<candidate>`.

Every read and probe rechecks the committed public projection, refusing `WorkspaceContaminated` when names or bytes differ, a public entry is writable, or the workspace is inside either checkout. Top level must contain exactly real `public` and `scratch` directories. The public projection admits no symlink; scratch may hold arbitrary examiner entries, including symlinks, and workspace inspection never follows them. Probe argument resolution still refuses escapes through scratch symlinks. Projection reads use the optional git port with ambient GIT_* variables removed; unavailable git yields `InputUnreadable`, exit 1. The workspace and bundle contain no checkout location. These boundaries do not confine the examiner's own Bash process or paths an admitted program computes internally.

## Declaring public commands

The declaration is `.nwave/examine.json` in the committed tree; only the committed blob is read, never the working tree. It is one JSON object with a `commands` list and an optional `build` text:

```json
{"commands": [{"name": "greet", "path": "bin/greet"}], "build": "run the build that writes bin/greet"}
```

- `commands`: each entry has exactly the keys `name` and `path`. A name matches `[A-Za-z0-9][A-Za-z0-9_-]*` and is unique. A path is relative to the candidate and names the executable the build already wrote there. The path rule follows the host. On every host a path is refused when it is empty; when it is not valid UTF-8 text (an unpaired surrogate); when it starts with `/`, which makes it absolute; when it contains a NUL or other control character; or when a segment split on `/` is empty, `.` or `..`. On Windows a path is also refused when it starts with `\` (UNC or device), when it starts with a drive letter and a colon such as `C:`, and when a segment split on `\` is empty, `.` or `..`. Every other in-root file name is admitted and runs. On POSIX that includes a backslash inside a name (`bin/a\b`, `\tool`, `bin/a\..\b`), a colon inside a name (`bin/a:b`) and a name that starts like a drive (`C:tool`). The `chmod` command the examiner prints for a file without its execute bit is `chmod +x -- ` followed by the path shell-quoted, so it runs exactly as printed for every admitted path.
- `build`: optional text shown only in refusal remedies. The examiner never runs it.

Unknown keys, duplicate keys and a document that is not a JSON object are refused with `InputUnreadable` naming the first violation. Each example below is run by a test in `tests/nwdes/acceptance/test_examine_declared_executables.py`.

### Rust

The build is `cargo build --release`; the declaration names the release binary. A test runs that build for real and skips where `cargo` is absent.

```json
{"commands": [{"name": "greet", "path": "target/release/greet"}], "build": "cargo build --release"}
```

### Go

The build is `go build`; the declaration names the binary it writes. The examiner does not run `go build`. The test runs the declared file through the same contract with a shell launcher standing in for the build output, so the `go` toolchain is not exercised by that test.

```json
{"commands": [{"name": "serve", "path": "bin/serve"}], "build": "go build -o bin/serve ."}
```

### Shell launcher

The declared file is a shell script with its executable bit, written or copied into the built location. Two commands, each with its own file, run under their own public names.

```json
{"commands": [{"name": "greet", "path": "bin/greet"}, {"name": "serve", "path": "bin/serve"}]}
```

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
