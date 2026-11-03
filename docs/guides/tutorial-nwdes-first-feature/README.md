# First feature with nwdes

Build a greeting command in a throwaway Git repository. You will create a handoff, declare one slice, fix an expectation, observe a failing behavior check, change the implementation, and record examination material.

**This is the one lesson where a person types the `nwdes` verbs.** You type them yourself for two reasons: to see how nwdes behaves — what it builds and how it guards what it records — and to learn what your root assistant will do for you in real work. Everywhere else nwdes is the assistant's tool: you point your assistant at the guides instead of typing the verbs. The sentence to paste is in [For your assistant](../README.md#for-your-assistant).

You need Python 3.11 or newer, Git, and an installed `nwdes` on your command path. No test library is needed. Use an empty temporary directory, not your real project. Each `Recorded output` block below comes from an executed run of that step; the role-recording steps, whose values here are fixtures, describe their effect instead of printing output.

**This lesson uses fixed role-output examples.** They teach the CLI boundary without a model call. They are explicitly marked as tutorial fixtures. They do not replace independent roles or prove a real delivery has passed review. For real work, use [Deliver a feature](../nwdes/deliver-feature.md).

## 1. Create an isolated project

Create an empty directory with your file manager and open a terminal there. Run:

```text
git init -b main
```

Recorded output:

```text
Initialized empty Git repository in /tmp/nwdes-docs-run/demo/.git/
```

nwdes records receipts under the Git directory, and every role `close` needs an existing HEAD. Create the bootstrap commit now:

```text
git commit --allow-empty -m 'lesson bootstrap'
```

If Git reports that no identity is configured, set one for this repository (`git config user.name 'Lesson'` and `git config user.email 'lesson@example.com'`), then repeat the commit. This creates HEAD; no lesson files are staged yet.

Create `global.json` with this content. This keeps global destination settings out of the lesson:

```json
{}
```

### Portable CLI wrapper

Create `tutorial_cli.py` with the following content. This is a Python wrapper
for this lesson, not an nwdes command or an installed nWave component. It passes
the recorded CLI arguments as a list and captures prompt output with a Python
file handle, so no shell quoting or output redirection is needed in PowerShell,
cmd.exe, or a POSIX shell.

Each step below first shows the plain `nwdes` command — the exact arguments
the wrapper passes to nwdes. Use the plain command when your shell handles
quoting and redirection comfortably; use the wrapper action when you would
rather not. The outputs shown are the same on both forms.

```python
import subprocess
import sys
from pathlib import Path

roots = ['--repo-root', '.', '--project-root', '.', '--global-config', 'global.json', '--feature', 'hello']
handoff = ['--handoff', 'docs/feature/hello/handoff.json']
commands = {
    'feature': ['feature', 'new', *roots, '--request', 'Print Hello, Ada! for Ada.', '--size', 'M', '--value', 'Greet a named user'],
    'slice': ['slice', 'set', *roots, '--observation', 'Ada receives Hello, Ada!', '--paradigm', 'procedural', '--oracle', 'test_greet.py', '--create', 'greet.py', '--stimulus', 'python greet.py Ada', '--expected', 'Hello, Ada!', '--falsifier', 'Any other output', '--command', 'python test_greet.py', '--promise', 'Ada receives Hello, Ada!'],
    'prompt-expectations': ['prompt', '--repo-root', '.', '--role', 'nw-user-examiner', '--task', 'expectations', *handoff],
    'expectations-row': ['expectations', 'row', 'add', *roots, '--promise', 'P1', '--text', 'Ada receives Hello, Ada!'],
    'expectations-close': ['expectations', 'close', *roots, '--outcome', 'accepted', '--diagnostic', 'Tutorial fixture, not an independent role result'],
    'prompt-examine': ['prompt', '--repo-root', '.', '--role', 'nw-user-examiner', '--task', 'examine', *handoff],
    'packet': ['packet', '--kind', 'examine', *handoff],
    'examine-observation': ['examine', 'observation', 'add', *roots, '--text', 'Tutorial fixture, not an independent observation: python greet.py Ada printed Hello, Ada!'],
    'examine-verdict': ['examine', 'verdict', 'set', *roots, '--expectation', 'E1', '--verdict', 'met', '--observation', 'O1'],
    'examine-close': ['examine', 'close', *roots, '--outcome', 'accepted', '--diagnostic', 'Tutorial fixture, not an independent role result'],
    'document': ['document', *roots],
    'delta': ['delta', '--previous', 'docs/feature/hello/handoff.json', '--new', 'docs/feature/hello/handoff.json'],
}
outputs = {'prompt-expectations': 'expectations-prompt.txt', 'prompt-examine': 'examination-prompt.txt'}
action = sys.argv[1]
command = ['nwdes', *commands[action]]
if action in outputs:
    with open(outputs[action], 'wb') as output:
        result = subprocess.run(command, stdout=output)
else:
    result = subprocess.run(command)
raise SystemExit(result.returncode)
```

Run:

```text
python tutorial_cli.py feature
```

Direct form (what the wrapper passes to nwdes):

```text
nwdes feature new --repo-root . --project-root . --global-config global.json --feature hello --request 'Print Hello, Ada! for Ada.' --size M --value 'Greet a named user'
```

Recorded output:

```text
WROTE docs/feature/hello/brief.md
WROTE docs/feature/hello/architecture.md
WROTE docs/feature/hello/acceptance.md
WROTE docs/feature/hello/brief.html
WROTE docs/feature/hello/architecture.html
WROTE docs/feature/hello/acceptance.html
WROTE docs/feature/hello/handoff.json
```

You now have the canonical handoff and its rendered outputs. Do not edit the handoff yourself.

## 2. Declare one observable slice

Direct form:

```text
nwdes slice set --repo-root . --project-root . --global-config global.json --feature hello --observation 'Ada receives Hello, Ada!' --paradigm procedural --oracle test_greet.py --create greet.py --stimulus 'python greet.py Ada' --expected 'Hello, Ada!' --falsifier 'Any other output' --command 'python test_greet.py' --promise 'Ada receives Hello, Ada!'
```

Or run the wrapper: `python tutorial_cli.py slice`.

Recorded output:

```text
WROTE docs/feature/hello/brief.md
WROTE docs/feature/hello/architecture.md
UNCHANGED docs/feature/hello/acceptance.md
WROTE docs/feature/hello/brief.html
WROTE docs/feature/hello/architecture.html
UNCHANGED docs/feature/hello/acceptance.html
WROTE docs/feature/hello/handoff.json
```

Omitting the slice option created S1. The promise has ID P1. The command is stored as a fact; nwdes did not run it.

`--paradigm` states the implementation style the slice uses: `procedural` (plain step-by-step code), `object_oriented`, or `functional`. The route dispatches the functional crafter when the paradigm is functional, otherwise the software crafter.

## 3. Fix an expectation

Generate the examiner's prompt:

```text
nwdes prompt --repo-root . --role nw-user-examiner --task expectations --handoff docs/feature/hello/handoff.json > expectations-prompt.txt
```

Or run the wrapper: `python tutorial_cli.py prompt-expectations` (it captures the file for you).

Jev, the remote judgment service, is authorized by default; this fixture-only lesson asks no Jev question, and the `TYPESAFE_API_KEY` environment variable is only its technical prerequisite. To refuse Jev, pass `--jev unauthorized` or declare `"jev": "unauthorized"` in `~/.nwave/config.json` — see [Understanding Jev](../understanding-jev.md).

The command writes one complete inline bundle to the file. Open it: it lists the public promises (P1 with its text) and the current fixed expectations — `None.` before the first fixation — and ends with the generated verb reference the role uses to record.

In a real delivery, that bundle goes to a fresh examiner, which records its rows from the user's point of view. Here you record the fixture row yourself with the same verbs:

```text
nwdes expectations row add --repo-root . --project-root . --global-config global.json --feature hello --promise P1 --text 'Ada receives Hello, Ada!'
nwdes expectations close --repo-root . --project-root . --global-config global.json --feature hello --outcome accepted --diagnostic 'Tutorial fixture, not an independent role result'
```

Or run the wrapper: `python tutorial_cli.py expectations-row`, then `python tutorial_cli.py expectations-close`.

The first `row add` creates the draft; `close` publishes it, assigns E1 to the row, and renders the outputs. Keep the expectation fixed while implementing.

## 4. Create the public check

Create `test_greet.py` with exactly this content:

```python
import subprocess
import sys

result = subprocess.run([sys.executable, 'greet.py', 'Ada'], capture_output=True, text=True)
setup_failed = result.returncode != 0
failed = not setup_failed and result.stdout != 'Hello, Ada!' + chr(10)
print(f'observed={int(not setup_failed)} failed_assertions={int(failed)} setup_failures={int(setup_failed)}')
raise SystemExit(int(setup_failed or failed))
```

In a real delivery, the acceptance designer would now record one Tested row for this oracle through its `nwdes acceptance` verbs — stimulus, expected result, user result, the promise it covers, the test locator, and `--still-passes-if` naming the nearest plausible wrong behaviour the test would still accept — and close. The exact flag list is printed in the designer's generated bundle; this lesson skips that recording and keeps the fixture honest.

## 5. Observe failure, then success

Create `greet.py` with the wrong behavior:

```python
import sys

print(f"Goodbye, {sys.argv[1]}!")
```

Run:

```text
python test_greet.py
```

Recorded output:

```text
observed=1 failed_assertions=1 setup_failures=0
```

The exit code is 1. The behavior assertion failed; setup succeeded.

Replace `greet.py` with:

```python
import sys

print(f"Hello, {sys.argv[1]}!")
```

Run the same check, then the public command:

```text
python test_greet.py
python greet.py Ada
```

Recorded output, in command order:

```text
observed=1 failed_assertions=0 setup_failures=0
Hello, Ada!
```

Both commands exit 0.

The root, not nwdes, runs these checks. This example accepts one required name. It does not promise missing-name handling or any other input behavior.

## 6. Build examination material

An optional charter — intent, exploration, at least one positive and one negative observation — can be recorded once for the feature with the `nwdes charter` verbs; this lesson skips it.

The examination packet projects the repository's committed files at HEAD, and the examiner's probe reads its console-script manifest from the committed `pyproject.toml`. The greeting is not a package, but the file must exist and be committed. Create `pyproject.toml`:

```toml
[project]
name = "hello"
version = "0.1.0"
```

Commit it together with the files created so far:

```text
git add -A
git commit -m 'Add project manifest'
```

Generate the examiner's examination prompt:

```text
nwdes prompt --repo-root . --role nw-user-examiner --task examine --handoff docs/feature/hello/handoff.json > examination-prompt.txt
```

Or run the wrapper: `python tutorial_cli.py prompt-examine` (it captures the file for you).

Print the examination packet:

```text
nwdes packet --kind examine --handoff docs/feature/hello/handoff.json
```

Or run the wrapper: `python tutorial_cli.py packet`.

The packet shows the public promises, the slice observations and public oracle, the fixed expectations, and the public-only examination workspace with its `nwdes examine read` and `nwdes examine probe` commands. It carries no host observations, no source paths and no private design records: the examiner gathers its own observations. Never supply an observation to a prompt or packet — those flags are refused by design.

In a real delivery the examiner works in the workspace the bundle names, records each observation itself, and cites only what it recorded. Here you record the fixture observation and verdict with the same verbs:

```text
nwdes examine observation add --repo-root . --project-root . --global-config global.json --feature hello --text 'Tutorial fixture, not an independent observation: python greet.py Ada printed Hello, Ada!'
nwdes examine verdict set --repo-root . --project-root . --global-config global.json --feature hello --expectation E1 --verdict met --observation O1
nwdes examine close --repo-root . --project-root . --global-config global.json --feature hello --outcome accepted --diagnostic 'Tutorial fixture, not an independent role result'
```

Or run the wrapper: `python tutorial_cli.py examine-observation`, then `examine-verdict`, then `examine-close`.

`observation add` prints its nwdes-issued ID (O1 here) — cite that printed ID, never an invented one. `close` stores the cited text with the verdicts and renders the acceptance brief. The fixture label remains the reason not to treat it as independent approval.

Then render and compare:

```text
nwdes document --repo-root . --project-root . --global-config global.json --feature hello
nwdes delta --previous docs/feature/hello/handoff.json --new docs/feature/hello/handoff.json
```

Or run the wrapper: `python tutorial_cli.py document`, then `delta`.

The delta prints nothing because both inputs are the same handoff. Open the acceptance brief to see the stored examination verdict.

## 7. Finish the lesson

You have practiced the command flow and observed the greeting through a real subprocess. Nothing was installed into your real host configuration, and no feature work was committed or integrated — the two commits in this lesson are scaffolding, not a delivered feature. You can remove the throwaway directory with your file manager when you no longer need it.

For real work, hand these verbs to your assistant — the sentence to paste is in [For your assistant](../README.md#for-your-assistant) — and continue with [Deliver a feature](../nwdes/deliver-feature.md), [Fix a bug](../nwdes/fix-bug.md), and [Use lanes](../nwdes/use-lanes.md). Look up flags in the [reference](../nwdes/reference/index.md).
