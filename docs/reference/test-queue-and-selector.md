# Test queue and test selector reference

`nwave-ai tests run` runs one test command of a project through the test queue of
the account. `nwave-ai tests select` lists the tests a change selects. Both read
what the project declares; neither names a language, a test runner or a
version-control tool. The only requirement is Python 3.11 or later.

`python3 -m nwave_ai.testrun ...` is the same command without an installed
`nwave-ai`: it needs the interpreter and the nWave tree.

## Synopsis

```
nwave-ai tests run [options] NAME [ARG ...]
nwave-ai tests run [options] -- COMMAND [ARG ...]
nwave-ai tests select --use NAME [options] [PATH ...]
```

| Option | Verb | Meaning |
|---|---|---|
| `--root DIR` | both | the project tree; default: the current directory |
| `--declaration FILE` | both | read the declaration from `FILE` instead of the `tests` block of `.nwave/config.json` |
| `--class NAME` | run | the class of the run; default: the declared command's class, else the last declared class |
| `--timeout SECONDS` | run | stop the command after this long; default: the declared command's limit, else none |
| `--receipt FILE` | run | also write the receipt to `FILE` |
| `--use NAME` | select | the declared use whose depth applies; required |
| `--add TEST` | select | also select this test; may be repeated |
| `--json` | select | print one JSON document instead of the list |
| `-h`, `--help` | both | print the usage |

## `nwave-ai tests run`

`NAME [ARG ...]` runs a command the project declares, with the further arguments
appended. `-- COMMAND [ARG ...]` runs any command as given. The command inherits the
standard streams and the environment, and runs in the project tree.

### The queue

- One queue per account: `<nWave home>/.nwave/test-queue/`, where the nWave
  home is `NWAVE_AGENTS_HOME` when set, else the account's home directory. Runs of
  every project and every worktree of the account wait in it. Two accounts on one
  machine have two queues and do not coordinate; neither do two nWave homes.
- Order: the classes the project declares, the first class first; inside a class,
  arrival order. A run of a later class that has waited `aging_seconds` goes before
  every run that has not, and nothing behind it starts first.
- Places: the lowest of the declared ceiling `max_concurrent`, the usable cores
  divided by `cores_per_run`, and the available memory divided by
  `memory_per_run_mb`; never fewer than one. When cores or memory cannot be read on
  the platform, one run at a time. A running run of a project with a lower ceiling
  keeps the lower ceiling for as long as it runs.
- The time limit starts when the command starts. The wait in the queue is measured
  apart and never counted in it. At the limit the command and every process it
  started are stopped.
- A run whose process dies leaves the queue: the next run that looks removes its
  ticket.
- A run whose process is alive keeps its place however long it runs: the queue
  never stops a run. The wait for a place is bounded instead, by the declared
  `max_wait_seconds`. A run that reaches it leaves the queue, runs nothing and
  ends `indeterminate` with exit 75 (see below).
- A run started inside a running run (the environment carries
  `NWAVE_TEST_QUEUE_TICKET`) starts at once: it already holds a place.

A waiting run prints one line on standard error:

```
[nwave tests] waiting: ticket 12, class long, 1 running, 2 waiting; gives up after 1800 s
```

Each ticket of the queue directory (`tickets/<n>.json`) records the class of the
run, the process that holds it (`pid`), its command, when it arrived
(`enqueued_at`) and when it started (`started_at`).

### A run that waits too long

When the wait reaches `max_wait_seconds` the run leaves the queue and prints, on
standard error, an `INDETERMINATE:` line and then `WHAT:`, `WHY:` and `HOW:`:

```
INDETERMINATE: this run is neither a pass nor a failure
WHAT: the run waited 1800.0 s for a place, reached the limit queue.max_wait_seconds of 1800 s and did not start; ahead of it: ticket 12, pid 4242, running for 2710 s: <command>
WHY: no test ran, so this is neither a pass nor a failure; a run that never ends keeps its place, and the queue does not stop another run
HOW: if a run ahead is stuck, stop its process (pid 4242): its place is free as soon as that process is gone; if it is only long, declare a larger queue.max_wait_seconds; then run this command again
```

`WHAT` names each run ahead: its ticket, its process, whether it is running or
waiting and for how long, and its command on one line. The runs ahead are the
running runs; when nothing runs, the run at the head of the line. The run ahead is
not touched. The figures above are an example.

### A run whose process is killed

A run does not start its command itself. It starts a supervisor process, in a
session of its own and held by a pipe, and the supervisor starts the command in a
process group of its own. When the pipe closes, the supervisor stops that group.
The pipe closes when the command's time limit is reached, when the run is asked
to end (interrupt, termination), and when the run's process disappears, whatever
killed it and at whatever moment: before, while or after the command starts.

When the supervisor itself disappears, the run stops the command's group and
ends `indeterminate` with exit 75: the exit of the command is unknown, so it is
neither a pass nor a failure.

Limits of this:

- it needs process groups (POSIX). Elsewhere the run starts the command itself
  and prints `NOTE: this platform has no process groups: if the process of this
  run is killed, its command keeps running`; it prints the same note, with the
  reason, when the supervisor cannot be started;
- a command that moves itself to another process group or session is not stopped;
- when the run and its supervisor are both killed, nothing stops the command;
- the place of the killed run is free as soon as its process is gone, which can
  be an instant before its command has ended.

### The receipt

Every run ends with one line on standard error, `[nwave tests] receipt: {...}`, and
the same JSON document in the `--receipt` file when one is named.

| Field | Meaning |
|---|---|
| `schema` | version of the receipt, `1` |
| `ticket` | the number of the run in the queue; for a nested run, its parent's |
| `class` | the class the run waited in |
| `root` | the project tree, resolved |
| `command` | the exact command, word by word |
| `candidate` | the identity of what was tested, one entry per declared reader; a reader that failed gives `{"unavailable": "<reason>"}` and a `NOTE` line; long or multi-line output is recorded as its SHA-256 |
| `outcome` | `completed`, `timed-out`, `not-started`, `refused` or `indeterminate` |
| `exit` | the command's exit code; `null` unless `completed` |
| `wait_seconds` | time spent waiting for a place |
| `duration_seconds` | time the command ran |
| `time_limit_seconds` | the limit applied, or `null` |
| `peak_memory_kb` | the largest resident set of the command's process, or of a process it waited for, as the system reports it for a finished child; it is not the sum over the processes of the command. `null` with `peak_memory_note` where the platform reports none |
| `events` | the queue's numbers of arrival, start and end: `enqueued < started < finished`, comparable across runs; `null` for a run that never started |
| `concurrency` | the number of places the run was admitted under |
| `nested` | `true` when the run started inside a running run |
| `refusal` | `what`, `why`, `how` when the run was refused, could not start or left the queue at its wait limit |

### Exit codes

| Code | Meaning |
|---|---|
| the command's own | the command ended; a command ended by signal `N` gives `128 + N` |
| `2` | the run was refused: nothing ran |
| `75` | the run left the queue at its wait limit: nothing ran, nothing was judged (`indeterminate`) |
| `124` | the time limit ended the command |
| `127` | the command could not be started |

### Refusals

A refusal prints three lines, `WHAT:`, `WHY:` and `HOW:`, and runs nothing. The run is
refused when the declaration is malformed (every defect is named at once), when the
class or the named command is not declared, when the time limit is not a positive
number, when the queue directory cannot be made or locked, and when the tool under
test resolves outside the tree:

- the project declares `tool_resolution.argv`, a command that prints the path or
  paths the tool under test resolves to;
- a path outside the project tree refuses the run (the known case: an editable
  installation that points at another checkout), and `HOW` carries the declared
  `repair`;
- a check that cannot run, exits non-zero or prints nothing also refuses: a check
  that cannot decide does not count as a pass.

## `nwave-ai tests select`

Prints the selected test files, sorted, one per line. The list is a function of the
changed paths, the declaration and the tree: the same change gives the same list, in
any order of the paths and with any repetition. `--add` joins tests to the list;
nothing removes one.

Rules, per changed path; a path may match several, and their union decides it:

1. a test file selects itself;
2. another file inside a test root selects the tests of its directory and below;
3. a path under a declared `assets` prefix selects the tests of the mapped
   directories;
4. a path whose file type has a dependency adapter selects the tests that depend on
   it, through any number of files, up to the depth of the use;
5. a path under a declared `no_tests` prefix selects nothing, by declaration;
6. a path no rule decides makes the selection **INDETERMINATE**.

The depth of a use bounds the dependency hops from a changed file outside the test
roots: `1` is the files that depend on it directly. A changed file inside a test
root is followed to every test that depends on it.

Standard error carries what the list alone does not say:

- `INDETERMINATE: <path>: <reason>` for each undecided path. The list is then the
  widest group the project declares (`widest`), united with what the decided paths
  reach. With no `widest` declared the selection is refused.
- `NOTE: no test depends on <path>` for a decided path that reaches no test.
- `OVER LOCAL CEILING: ...` when the list is longer than `local_ceiling`: the list
  is complete and is meant for the place that runs the wide groups, not for the
  machine.

`--json` prints `outcome` (`selected` or `indeterminate`), `use`, `depth`, `tests`,
`reached` (what the decided paths reach, with the added tests), `added`,
`undecided` (`path`, `reason`), `uncovered`, `local_ceiling` and
`over_local_ceiling`.

### Dependency adapters

How the files of one language depend on each other is an adapter, named per file
extension in `selection.adapters`. This version ships one, `python`:

- imports, absolute and relative, with the packages on the way;
- a module named in text (`importlib.import_module("a.b")`, a patch target);
- a module started as a separate process (`python -m a` reaches `a/__main__.py`)
  and a script started by its path;
- a project file named by its path, as text or built with `/`;
- the files declared `implicit` (for example `conftest.py`) in the file's directory
  and above.

Settings, under `selection.python`: `import_roots` (default `["."]`) and `implicit`
(default none). A module name or a path assembled at run time is not seen. A file
that does not parse is treated as depending on every file its text names.

An extension with no adapter, or with an adapter name this version does not have,
is not guessed: its files are undecided. To add a language, add a module with the
two functions of `nwave_ai.testrun.selection.DependencyAdapter` and name it in
`nwave_ai/testrun/dependency_adapters.py`; the selector itself does not change.

## The declaration

The `tests` block of `.nwave/config.json`: the project's file, else the global one
(the project block replaces the global block whole). `--declaration FILE` reads a
file whose root object is that block. Every key is optional; an unknown key is a
defect, and all defects are reported together.

```json
{
  "tests": {
    "queue": {
      "classes": ["short", "long"],
      "aging_seconds": 1200,
      "max_wait_seconds": 1800,
      "max_concurrent": 1,
      "cores_per_run": 1,
      "memory_per_run_mb": 2048
    },
    "commands": {
      "focused": {"argv": ["<runner>", "<arguments>"], "class": "short", "timeout_seconds": 300}
    },
    "candidate": {"commit": ["<command that prints the commit>"]},
    "tool_resolution": {
      "argv": ["<command that prints where the tool resolves>"],
      "repair": "<how to make it resolve inside the tree>"
    },
    "selection": {
      "test_roots": ["tests"],
      "test_files": ["test_*.py"],
      "adapters": {".py": "python"},
      "python": {"import_roots": ["src", "."], "implicit": ["conftest.py"]},
      "assets": {"<path prefix>": ["<test directory>"]},
      "no_tests": ["docs/"],
      "widest": ["tests"],
      "local_ceiling": 200,
      "uses": {"commit": 1, "review": "transitive"},
      "ignore": ["<directory name not to read>"]
    }
  }
}
```

| Key | Default | Meaning |
|---|---|---|
| `queue.classes` | `["short", "long"]` | the classes, in the order they go |
| `queue.aging_seconds` | `1200` | wait after which a run of a later class goes first |
| `queue.max_wait_seconds` | `1800` | wait after which a run leaves the queue unrun (`indeterminate`, exit 75). The default is longer than the aging threshold, so an aged run still gets its turn, and short enough that a run which never ends costs a waiting run minutes, not a working session; a project whose runs are longer declares more |
| `queue.max_concurrent` | `1` | ceiling of runs at once |
| `queue.cores_per_run` | `1` | cores one run needs |
| `queue.memory_per_run_mb` | `2048` | memory one run needs |
| `commands.<name>` | none | a command run by name: `argv`, optional `class` and `timeout_seconds` |
| `candidate.<name>` | none | a command whose output identifies what is tested |
| `tool_resolution` | none | `argv` and optional `repair`; absent, nothing is checked |
| `selection` | none | absent, `select` is refused |
| `selection.test_roots` | required | directories that hold the tests |
| `selection.test_files` | required | name patterns of test files |
| `selection.uses` | required | depth per use: a whole number of hops or `"transitive"` |
| `selection.adapters` | none | adapter name per file extension |
| `selection.<adapter name>` | none | settings of that adapter |
| `selection.assets` | none | path prefix to the test directories that assert on it |
| `selection.no_tests` | none | path prefixes from which no test derives |
| `selection.widest` | none | directories of the widest group, the fallback when indeterminate |
| `selection.local_ceiling` | none | list length above which the list is flagged as not for this machine |
| `selection.ignore` | none | directory names not read; hidden directories are never read |

With no `tests` block the queue still works: classes `short` and `long`, one run at
a time, no check and no candidate identity.

## What this does not do

- The queue orders and bounds the runs that go through it. A test run started
  another way is neither seen nor counted.
- The locks are advisory file locks on the queue directory: a file system that does
  not honour them across processes does not serialise the runs.
- The selector lists test files, not single tests.
- The selector reads files; it does not run the project. A dependency that exists
  only at run time is outside the list.
- The queue never stops a run. A run that never ends keeps its place until its
  owner stops it; the runs behind it give up at `max_wait_seconds` and name it.
- The queue is one per account. Two accounts on one machine, or two nWave homes,
  have two queues: their runs are neither ordered nor counted together.
- A command that leaves its process group outlives a killed run; see "A run whose
  process is killed".
- A low depth does not reach a test that exercises a changed file through other
  files, for example through a command's entry point. The list of a use that
  declares `"transitive"` does.
