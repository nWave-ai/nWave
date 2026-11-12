# nWave CLI Reference

The `nwave-ai` command-line tool installs, configures, and manages the nWave framework in supported agentic hosts. For hands-on setup, see the **[Installation Guide](../guides/installation-guide/README.md)**. For per-project activation, see the **[Activation Guide](../guides/activating-nwave-per-project.md)**.

## Invocation

Commands are invoked as:

```
nwave-ai <command> [options] [arguments]
```

Alternatively, use Python's module syntax:

```
python -m nwave_ai.cli <command> [options] [arguments]
```

## Synopsis

Observed `--help` behaviour: `nwave-ai status --help` exits 0 but prints the status report instead of usage; `nwave-ai install --help` and `nwave-ai uninstall --help` exit 0 and print their own usage (the uninstall text names `python uninstall_nwave.py`); `nwave-ai rigor --help` exits 2 and prints its usage line after WHAT/WHY/HOW lines; `nwave-ai attribution --help` and `nwave-ai mode --help` exit 1.

```
nwave-ai install [--platform <tool>] [--target <path>] [--yes]
                 [--dry-run] [--backup-only] [--restore]

nwave-ai uninstall [--target <path>]

nwave-ai doctor [--json] [--fix]

nwave-ai attribution <on|off|status>

nwave-ai model set --provider {codex,claude} --model MODEL [--role ROLE] [--project]

nwave-ai rigor [--show] [--yes] [--models keep | --model-set GROUP_OR_ROLE=PROVIDER/MODEL ...] [--review-rounds 1-5|current] [--examine-level quick|standard|extended|current] [--documents yes|no|keep [--document-language LANG]] [--hosts HOST[,HOST...]|none|keep]

nwave-ai project <enable|disable>

nwave-ai mode <all|opt-in>

nwave-ai status

nwave-ai completion <bash|zsh>

nwave-ai version

nwave-ai --version

nwave-ai outcomes [--registry PATH] register | check

nwave-ai plugin <list|install|uninstall> [name]

```

---

## nwave-ai install

Install nWave into the selected host's configuration directories. `--target` selects a custom Claude configuration directory; native OMP installation uses its own discovery roots. Installation does not ask for or write documentation-density preferences.

### Synopsis

```
nwave-ai install [--platform <tool>] [--target <path>] [--yes] \
                 [--dry-run] [--backup-only] [--restore]
```

### Flags

| Flag              | Required | Type   | Description                                                                |
|-------------------|----------|--------|----------------------------------------------------------------------------|
| `--platform`      | no       | enum   | Target agentic tool: `auto`, `claude-code`, `codex`, `cursor`, `opencode`, `copilot`, `omp`, `devin`, or `all`; `auto` infers available hosts and refuses when none are detected. Forwarded to the installer subprocess. |
| `--target`        | no       | path   | Install into <path> instead of `~/.claude/`. Must not be `$HOME` (rejected with exit 2). Sets `CLAUDE_CONFIG_DIR` for subprocess. Default: `~/.claude/`. |
| `--yes`           | no       | bool   | Non-interactive mode. Recommended for CI. |
| `--density-only`  | no       | bool   | Run only the first-run documentation density prompt and exit (test-driving fixture; not a user flag). Exit 0 on completion. |
| `--dry-run`       | no       | bool   | Preview changes without modifying the filesystem. Passed through to install script. |
| `--backup-only`   | no       | bool   | Create a backup only without installing. Passed through to install script. |
| `--restore`       | no       | bool   | Restore nWave from a previous backup. Passed through to install script. |

**Pass-through behavior**: All flags except `--yes` and `--target` are forwarded to `scripts/install/install_nwave.py`. `--target` sets `CLAUDE_CONFIG_DIR` for the subprocess; `--yes` selects non-interactive mode.

For `--platform omp`, public skills and native task agents use OMP's separate discovery roots. `PI_CONFIG_DIR` selects the configuration-root name under the user home; `PI_CODING_AGENT_DIR` selects the native skill/data root when set. Named `OMP_PROFILE`/`PI_PROFILE` installations are refused rather than silently writing to the default profile. The installer reports capabilities that OMP cannot project, including Claude-specific hooks and unsupported scoped tool permissions. User-owned skills and agents are not nWave-managed assets.

### Exit codes

| Code | Condition                                                              |
|------|--------|
| 0    | Installation succeeded. Package manager recorded in global config if needed. |
| 1    | Installation failed (subprocess error). |
| 2    | Configuration error: `--target` points to `$HOME`, or `--target` argument missing. |

### Output

Installation reports its actual installer result; it does not report a
documentation-density preference being written.
**stderr** on error:

```
nwave-ai: --target must point to a config directory (e.g. ~/.claude-nwave or ./.claude), not your home directory
```

### Example

```bash
# First-time install, without a density prompt
nwave-ai install

# CI environment: no user interaction
nwave-ai install --yes

# Install to a custom Claude config directory
nwave-ai install --target ~/.claude-nwave

# Dry-run to see what would be changed
nwave-ai install --dry-run

# Restore from backup after a failed upgrade
nwave-ai install --restore
```

---

## nwave-ai uninstall

Remove the nWave framework from configured tool directories. Project files
(`.nwave/`, source code) are not touched; only the framework itself is
removed.

### Synopsis

```
nwave-ai uninstall [--target <path>]
```

### Flags

| Flag       | Required | Type | Description                                                          |
|------------|----------|------|------|
| `--target` | no       | path | Uninstall from <path> instead of assistant default config path. Must not be `$HOME` (rejected with exit 2). Sets `CLAUDE_CONFIG_DIR` for subprocess. |

### Exit codes

| Code | Condition                                                    |
|------|------|
| 0    | Uninstallation succeeded.                                    |
| 1    | Uninstallation failed (subprocess error or I/O failure).     |
| 2    | Configuration error: `--target` points to `$HOME`.           |

### Output

**stdout** on success (subprocess-dependent, typically minimal).

**stderr** on error (subprocess-dependent).

### Example

```bash
nwave-ai uninstall

nwave-ai uninstall --target ~/.claude-nwave
```

---

## nwave-ai doctor

Run diagnostics on the nWave installation. Checks for missing files, broken configuration, and hook integrity. Use `--json` for machine-readable output or `--fix` to attempt repairs (currently not yet implemented).

### Synopsis

```
nwave-ai doctor [--json] [--fix] [--help]
```

### Flags

| Flag     | Required | Type | Description                                                                   |
|----------|----------|------|-----|
| `--json` | no       | bool | Emit JSON output instead of human-readable text (suitable for scripting).     |
| `--fix`  | no       | bool | Attempt to fix detected issues. Currently not implemented; exits 2.           |
| `--help` | no       | bool | Print help message and exit (exit 0).                                         |

### Exit codes

| Code | Condition                                                       |
|------|------|
| 0    | All diagnostic checks passed.                                   |
| 1    | One or more checks failed (unhealthy installation).             |
| 2    | Misconfiguration or unimplemented flag (`--fix` without support). |

### Output

**stdout** on check pass (human):

```
✓ python_version: OK
✓ framework_files: OK
✓ hooks_registered: OK
✓ hook_python_path: OK
✓ config_ssot: OK
✓ attribution: OK
✓ version_sync: OK
```

The report lists one line per installed check; a failing check shows its
diagnostic and a remediation line instead of `OK`.

**stdout** on check failure (human):

```
✗ config_ssot: the configuration file could not be read or parsed
```
**stdout** on `--json`:

```json
{
  "checks": [
    {
      "name": "config_ssot",
      "passed": true,
      "message": "OK"
    }
  ],
  "summary": "All checks passed"
}
```

### Example

```bash
nwave-ai doctor

nwave-ai doctor --json | jq '.summary'

nwave-ai doctor --fix
# → --fix not yet implemented. Run `nwave-ai install` to restore a broken installation.
# → (exit 2)
```

## nwave-ai model

Select the provider and model for nWave roles. Records an explicit
provider/model pair in `model_runtime` (`model_runtime.default`, or
`model_runtime.roles.<role>` with `--role`) instead of deriving a model from
a competence label.

### Synopsis

```
nwave-ai model set --provider {codex,claude} --model MODEL [--role ROLE [--competence COMPETENCE]] [--project]
```

Without `--project` the global default is updated; with `--project` the
project's `.nwave/config.json` is written instead. With `--role`, that role
is updated instead of the tier default. The supported providers are `codex`
and `claude`; whether your host consumes `model_runtime` depends on that
host's model-configuration support (see
[Assigning models to roles](../guides/assigning-models-to-roles.md)).

`nwave-ai rigor` writes its per-role entries into the same `model_runtime.roles` store that `model set --role` writes, and it reads both the project and the global file. A per-role entry from `model set --role` (without `--competence`) appears in [`nwave-ai rigor --show`](#nwave-ai-rigor). A default from `model set` without `--role` does not: `--show` lists per-role entries only. `model set` keeps its meaning; rigor does not replace it.


---

## nwave-ai rigor

Choose this project's quality scope: the model for each role, the review-round limit, the examine level, and whether readable documents for people are produced. Run it from the repository root. It is not the `nw-rigor` skill, which keeps using `nwave-ai model set`. On a terminal the command asks each missing question one at a time, showing the current value and its source. A script answers every question with an option. It writes nothing until the final summary is confirmed, or until `--yes` is given.

### Synopsis

```
nwave-ai rigor [--show] [--yes] [--models keep | --model-set GROUP_OR_ROLE=PROVIDER/MODEL ...] [--review-rounds 1-5|current] [--examine-level quick|standard|extended|current] [--documents yes|no|keep [--document-language LANG]] [--hosts HOST[,HOST...]|none|keep]
```

### Answers

`--models`, `--review-rounds`, `--documents` and `--hosts` each need one answer. On a terminal the command asks each missing one, one question at a time: Enter keeps the value in effect, and a wrong answer asks the same question again. With `--yes` it never asks: a missing answer refuses with exit 2 and names every missing option. Without `--yes` and without a terminal (stdin at end of input, for example `</dev/null` or an empty pipe), it refuses with exit 2 and names every question that has no answer, for example `no answer arrived for 5 questions: --models, --review-rounds, --examine-level, --documents, --hosts. The terminal closed.` The examine level is listed there because it is asked as well, although `--examine-level` is optional. A fully closed stdin (`0<&-`) was not measured after this change. Scripts must therefore pass `--yes` and all four answers, for example `--yes --models keep --review-rounds current --documents keep --hosts keep`. On a terminal the models question takes one `target=provider/model` pair; for several, use the options.

### Flags

| Flag | Required | Type | Description |
|------|----------|------|-------------|
| `--show` | no | bool | Print the effective value of every role model, the review rounds, the examine level and the documents choice, each with its source. Writes nothing. Other options are not applied when `--show` is given. |
| `--yes` | no | bool | Confirm the final summary without asking. Every answer must then be given as an option. A host named by `--hosts` is written under this confirmation too. |
| `--models` | answer | `keep` | Leave every role model unchanged. Only `keep` is accepted here; set models with `--model-set`. |
| `--model-set` | answer | `GROUP_OR_ROLE=PROVIDER/MODEL` | Repeatable; several values may follow one option. `GROUP_OR_ROLE` is `producers` (roles whose tools include Write or Edit), `reviewers` (names ending `-reviewer`), `executors` (names ending `-crafter`), or one published role name. Groups overlap. Values apply in the order given, so give a group first and a single-role override after it. The provider is the text before the first `/` and the model is the rest; both are stored as given, with no availability check and no fallback. |
| `--review-rounds` | answer | `1-5` or `current` | The review limit per finding: a whole number from 1 to 5. `current` keeps the value in effect. |
| `--examine-level` | no | `quick`, `standard`, `extended` or `current` | The examine level: how many examinations a delivery admits. `quick` admits 1 examination and no repair round; `standard` (the built-in default) admits 2 examinations and one repair round; `extended` admits 3 examinations and two repair rounds. A level limits only the examinations, as the review rounds limit reviews. `current` keeps the value in effect, and an omitted option means `current`. A terminal session asks this question after the review rounds; Enter keeps the level in effect, and a wrong answer asks again. |
| `--documents` | answer | `yes`, `no` or `keep` | Whether to produce a readable HTML brief for people at the charter and design closes. `keep` leaves the setting unchanged. |
| `--document-language` | no | text | Language of the readable brief. Default `en`, stored as given. With `--yes`, `--documents yes` also needs this option. |
| `--hosts` | answer | `HOST[,HOST...]`, `none` or `keep` | Host configuration files to write the model facts into. Host names: `omp`, `claude-code`, `codex`, `copilot`, `opencode`, `devin`. `none` and `keep` write no host file. See [Host files](#host-files). |

### Exit codes

| Code | Condition |
|------|-----------|
| 0    | The project file was written, or `--show` printed. A host that cannot take per-role models prints its refusal; the project file is still written and the command still exits 0. |
| 1    | The project file could not be written (not writable, or a config migration conflict). Nothing was written, host files included. |
| 2    | Refusal, with WHAT, WHY and HOW lines on stderr: an unknown or repeated option; a role name that is not published; review rounds outside 1 to 5; an answer missing with no terminal to ask; an unconfirmed summary; an unreadable project or global config file; a model fact that matches no published role; an unknown host name; `--documents yes` with `--yes` and no `--document-language`. Nothing was written. |

### Output

`--show` prints one line per published role, then the review limit and the documents choice:

```
role nw-acceptance-designer: claude-opus-5 (built-in default)
role nw-acceptance-designer-reviewer: claude/opus-4-6 (project)
review rounds: 3 (project)
examine level: standard (built-in default)
  gives: 2 examinations, 1 repair round
  not covered at this level: more than 1 repair round
  not covered at any level: security, load or checks on other machines
  a row not examined is never green
documents: yes, language en (project)
```

The built-in defaults are 2 review rounds, examine level `standard` and documents `yes` in English. The default applies if no level declares `documents.readable_brief`. If the readable brief is on, the command checks each markdown brief that it writes. A diagram without exactly one non-empty `%% alt:` line, or with more than 25 distinct nodes, refuses the command. The refusal names the brief file and the diagram. The command writes no file. `--documents no` turns the brief and the check off. See [document](../guides/nwdes/reference/document.md#readable-brief-check) for the briefs that are checked.

On a terminal, each question prints its name, what it is, why change it, its answers, its default and where to see it later, then its answer line. The models question gives one example, `producers=claude/opus-4-6`, and says that running `nwave-ai rigor` again changes the models. The documents question says the language question, number 5, is asked only after yes. The review rounds question explains the trade-off: few rounds can leave defects unseen; many rounds can find new things and never stop. When a finding is still open at the limit, the work stops and the finding goes to its owner. Reaching the limit is never an approval.

A write prints the final summary first. The Git sentence comes before the confirmation question, so you read it before you answer yes. A kept examine level shows as `keep`, with its source:

```
Final summary - read before you confirm
  review rounds: 3 (was 2, built-in default)
  examine level: quick (was standard, built-in default)
    gives: 1 examination, no repair round
    not covered: any repair round, security, load or checks on other machines
    a row not examined is never green
  documents: yes, language en (was no, built-in default)
  model nw-documentarist: codex/gpt-5
  hosts: none
The project file .nwave/config.json: this file may be tracked by Git,
depending on your .gitignore.
Nothing is written until you answer yes.
confirm the final summary? (yes):
Written /path/to/repo/.nwave/config.json (project).
```

Whether the project file is tracked by Git depends on the repository's `.gitignore`. Run `git status` before you commit it.

### Files written

The project file `.nwave/config.json` in the current directory receives:

- `review.max_rounds`, when the rounds answer is a number. `current` writes nothing.
- `examine.level`, as `{"level": NAME}`, when the examine answer names a level. `current` and an omitted `--examine-level` write nothing.
- `documents.readable_brief` as `{"enabled": true|false, "language": LANG}`, when `--documents` is `yes` or `no`.
- `model_runtime.roles.<role>` as `{"provider": ..., "model": ...}`, for each role a model fact names. A group names every published role of that group.

Top-level keys that rigor does not write are kept. When it writes `review` or `documents`, it replaces that whole object, so a nested key inside it that rigor does not write is dropped. The global file is read but never written. `documentation`, `rigor.profile` and `model_runtime.default` are not written.

### Host files

Only the hosts you name and confirm are written. Paths are under your home directory.

| Host | File | Format status |
|------|------|---------------|
| `omp` | `.omp/agent/config.yml`, key `task.agentModelOverrides`. The file must already exist: without it the adapter reports a refusal naming `cannot access local variable 'task'`, the command still exits 0, and the project file is still written (observed). | Verified on this machine for an existing file. Comments in that YAML file are lost. |
| `claude-code` | `.claude/agents/nw/<role>.md`, a `model:` line; the file is created when absent | Verified. Accepts only the `claude` provider and writes `claude-<model>`. An nWave reinstall regenerates these files. |
| `opencode` | `.config/opencode/opencode.json`, key `agents.<role>.model` | Documented, not verified on this machine (version 2 format). |
| `copilot` | `.copilot/agents/<role>.agent.md`, a `model:` frontmatter line | Documented only for provider-qualified local models; not verified. |
| `codex` | none | Refuses: the config has one top-level `model` and no per-role surface. |
| `devin` | none | Refuses: the documented config has one default model and no per-role surface. |

The summary shows each host's path before the write. Unverified formats are labelled `format not verified: format NAME assumed from source URL`. The previous bytes are kept beside the file as `NAME.nwave-bak`, and an existing backup is never overwritten. A host file whose content does not match the documented shape is not written.

### Which routes read these settings

- The spine route (`nwdes prompt`) reads `review.max_rounds`, `examine.level`, `model_runtime.roles` and `documents.readable_brief` from the project file and the global file, project first. It prints them in each role bundle: `review rounds: N (source)`, `examine level: NAME (source) - N examinations, ...`, and `model <role>: provider/model (source)` or `none declared in project or global`. The examiner bundle states the level in examinations and repair rounds only. The readable-brief line appears only in the charter-close and design-close bundles, and only when enabled. A review value outside 1 to 5 or an examine level outside quick, standard and extended makes the bundle refuse, naming the key. The bundle states the model; `nwdes` starts no model.
- Dynamic mode (`/nw-dynamic`, the `nwstep` route) reads `examine.level` (and `jev`) from the project file and the global file, project first, and fixes it in the run workspace at `nwstep prompt`, in `examine-level.json`. It still does not read `review.max_rounds`, `model_runtime` or `documents.readable_brief` through the tool. In interactive mode only, the host procedure in `nWave/tasks/nw/dynamic.md` reads `documents.readable_brief` and, when it is enabled, adds the readable-output block to the request file and runs one documentarist round; no tool checks that the executor follows it. The dynamic examine step (`dynamic-v9`, after `handoff`) records an examiner's id and one line per fixed row; the level's repair rounds are enforced by the nwdes examination. Host files from `--hosts` are host configuration; whether a dynamic run uses them depends on how the host starts its executor, which nWave does not check.

### Example

```bash
# What is in effect (writes nothing)
nwave-ai rigor --show

# Group, then one role; rounds 3; readable brief in English; no host file
nwave-ai rigor --yes --model-set reviewers=claude/opus-4-6 --model-set nw-documentarist=codex/gpt-5 --review-rounds 3 --documents yes --document-language en --hosts none

# Keep every current value; still writes the project file
nwave-ai rigor --yes --models keep --review-rounds current --documents keep --hosts keep
```

---

## nwave-ai version

Print the installed nWave version and exit.

### Synopsis

```
nwave-ai version

nwave-ai --version

nwave-ai -V
```

### Exit codes

| Code | Condition                 |
|------|------|
| 0    | Version printed successfully. |

### Output

**stdout**:

```
nwave-ai 1.1.0
```

### Example

```bash
nwave-ai version

nwave-ai --version

nwave-ai -V
```

---

## nwave-ai attribution

Enable or disable automatic commit attribution. When enabled, nWave adds a `Co-Authored-By:` trailer to commits made inside Claude Code hooks.

### Synopsis

```
nwave-ai attribution <on|off|status>
```

### Positional arguments

| Argument | Required | Type | Description                                   |
|----------|----------|------|------|
| action   | yes      | enum | One of `on`, `off`, or `status`.               |

### Exit codes

| Code | Condition                                           |
|------|------|
| 0    | Action completed successfully.                      |
| 1    | Invalid action (not `on`, `off`, or `status`).      |

### Output

`on` and `off` write the machine preference. A project override takes
precedence; credit also requires an active project and a supported commit
hook. These commands do not change project activation or overrides.

**stdout** on `attribution on`:

```
Attribution enabled. New Claude commits will carry the nWave credit via the universal handler (observes the preference at commit time).
```

**stdout** on `attribution off`:

```
Attribution disabled. New Claude commits will not carry the nWave credit (the universal handler observes the preference at commit time).
```

**stdout** on `attribution status` with an active project override:

```
Attribution is currently on.
Preference source: project.
Attribution is active for this repo.
```

`status` reads the effective preference (project, global, or default) and
reports attribution as inactive if the project is inactive or the preference
is off. It does not change any configuration.

**stderr** on invalid action:

```
Unknown attribution action: invalid
Usage: nwave-ai attribution <on|off|status>
```

### Example

```bash
nwave-ai attribution on

nwave-ai attribution status

nwave-ai attribution off
```

---

## nwave-ai project

Enable or disable nWave activation for the current project repository. Writes `.nwave/config.json` with `enabled: true|false` as a version-controlled marker and reconciles `.gitignore` so the marker stays tracked.

### Synopsis

```
nwave-ai project <enable|disable>
```

### Positional arguments

| Argument | Required | Type | Description                                    |
|----------|----------|------|------|
| action   | yes      | enum | One of `enable` or `disable`.                  |

### Exit codes

| Code | Condition                                                |
|------|------|
| 0    | Marker written and gitignore reconciled.                 |
| 1    | Invalid action (not `enable` or `disable`).              |

### Output

**stdout** on success:

```
nWave activation for this project: enabled.
```

or

```
nWave activation for this project: disabled (sticky opt-out).
```

**stderr** on invalid action:

```
Usage: nwave-ai project <enable|disable>
```

### Details

- **enable**: Writes `"enabled": true` into `.nwave/config.json` and fixes `.gitignore` to allow the marker file.
- **disable**: Writes `"enabled": false` into `.nwave/config.json` (sticky opt-out; the recorded value signals explicit non-participation).

See the **[Activation Guide](../guides/activating-nwave-per-project.md)** for the full concept and workflow.

### Example

```bash
nwave-ai project enable

nwave-ai project disable
```

---

## nwave-ai mode

Set the global activation mode for nWave across all projects. Writes to `~/.nwave/config.json` under the key `activation.mode`.

### Synopsis

```
nwave-ai mode <all|opt-in>
```

### Positional arguments

| Argument | Required | Type | Description                                    |
|----------|----------|------|------|
| mode     | yes      | enum | One of `all` or `opt-in`.                      |

### Exit codes

| Code | Condition                                     |
|------|------|
| 0    | Mode written successfully.                    |
| 1    | Invalid mode (not `all` or `opt-in`).         |

### Output

**stdout** on success:

```
Global nWave activation mode set to 'all'.
```

or

```
Global nWave activation mode set to 'opt-in'.
```

**stderr** on invalid mode:

```
Usage: nwave-ai mode <all|opt-in>
```

### Details

- **all**: Enable nWave for all projects by default (unless explicitly disabled per-project).
- **opt-in**: Disable nWave globally; activate only per-project via `nwave-ai project enable`.

See **[Global Config Reference](./global-config.md)** for the full schema.

### Example

```bash
nwave-ai mode all

nwave-ai mode opt-in
```

---

## nwave-ai status

Show effective activation, attribution, verbosity, running CLI version, and
detected Claude Code/Codex assets with the source of each setting. Labels
distinguish detected host files from a validated installation. Persisted
`update_check` is retired and ignored. Documentation density is diagnostic-only;
the global expansion preference controls optional explanation after completed
waves. This command reads local state without writing files or checking releases.

### Synopsis

```
nwave-ai status
```

### Exit codes

| Code | Condition         |
|------|------|
| 0    | Status printed.   |
| 1    | Invalid selected home override; no status printed. |

### Output

**stdout**, for example:

```
Global activation mode: opt-in (default)
This project is active.
Activation source: project.
Version: 4.0.0 (running CLI; check releases: nwave-ai update --check)
Attribution: off (global); nWave co-author credit will not be added here.
Verbosity: terse (global).
Claude Code: framework files found.
Codex: installation manifests not detected.
Retired update_check: ignored (global); no automatic update prompt.
Documentation density: diagnostic-only (global); does not reshape waves.
Wave-end explanation: ask-intelligent (default; after completed waves only).
To credit future nWave commits: nwave-ai attribution on (machine-wide).
Host detection is not validation; use nwave-ai doctor for Claude Code or the Codex installer's validation.
```

Activation and other settings can come from a project override, the machine
config, or a default. An inactive repo instead shows
`nwave-ai project enable`. Status does not turn attribution on automatically.

### Example

```bash
nwave-ai status
```

---

## nwave-ai completion

Print a shell-completion script for Bash or Zsh to stdout. Source the output in your shell startup file.

### Synopsis

```
nwave-ai completion <bash|zsh>
```

### Positional arguments

| Argument | Required | Type | Description                    |
|----------|----------|------|------|
| shell    | yes      | enum | One of `bash` or `zsh`.        |

### Exit codes

| Code | Condition                                   |
|------|------|
| 0    | Completion script printed successfully.     |
| 1    | Unsupported or missing shell argument.      |

### Output

**stdout** (Bash example):

```bash
_nwave_ai_completion() {
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local prev="${COMP_WORDS[COMP_CWORD-1]}"

  # Completion logic here
  COMPREPLY=( $(compgen -W "install uninstall doctor version status" -- "$cur") )
}
complete -o bashdefault -o default -o nospace -F _nwave_ai_completion nwave-ai
```

**stderr** on unsupported shell:

```
Unsupported completion shell: 'fish'
Usage: nwave-ai completion <bash|zsh>
```

### Example

```bash
# Bash: add to ~/.bashrc
nwave-ai completion bash >> ~/.bashrc
source ~/.bashrc

# Zsh: add to ~/.zshrc
nwave-ai completion zsh >> ~/.zshrc
source ~/.zshrc
```

---

## Advanced commands

The following subcommands are supported but are not part of the everyday user surface. Refer to their sources or existing documentation for details:

- **outcomes** — Register / check shipped outcomes (Tier-1 collision detection). See **[Outcomes CLI Reference](./outcomes-cli.md)**.
- **plugin** — Install, uninstall, or list nWave tool plugins.

---

## nwdes

`nwdes` is the delivery tool. It builds role prompts and packets, writes handoff and authority records, and manages lanes. It starts no model and runs no verification command. The command list, arguments, refusals and an example for each verb come from `nwdes --help` and `nwdes VERB --help`.

### Route facts

| Fact | Behavior |
|------|----------|
| Roots | `--repo-root` defaults to the current directory and `--project-root` to the repository root. Lane verbs resolve the main worktree. |
| First recording | The first `add`, `set` or `remove` of a role kind creates its scoped draft. |
| Revision | `open --from-current` seeds a draft from published authority. It is not a first call. |
| Close | `close --outcome OUTCOME --diagnostic TEXT` publishes the draft and removes it. A refusal keeps the draft for correction. |
| Abort | `abort` removes the draft. |
| Values | Roles record typed values with CLI flags or `--FIELD-file PATH`. The root submits no role output. |
| Lane | `nwdes lane integrate` fast-forwards trunk to CANDIDATE, then removes the lane worktree and branch without force. |

### Prompt

```
nwdes prompt --role ROLE --handoff PATH [--jev {authorized,unauthorized}] [--task TASK] [--slice ID] [--phase PHASE] [--diff PATH] [--root-context TEXT]
```

`--jev` is optional and `authorized` by default: when neither the flag nor a
configuration tier declares `jev`, the resolved authorization is `authorized`
(the flag wins over the repository tier, which wins over the global tier; a
malformed value is refused; nwdes never writes or persists the key).

The output is one complete inline role bundle that ends with the generated verb reference for that role. See the **[prompt contract](../guides/nwdes/reference/prompt.md)** and the **[nwdes command reference](../guides/nwdes/reference/index.md)**.

### Source-blind examiner prompts

The examiner works from the user's point of view and needs only public product facts. Pass only public text in `--root-context`; it is rendered verbatim. The examiner prompt replaces the preloaded `nw-typesafe-system-one` client recipe with the skill's source-blind EXAMINE limit notice (do not call Jev; report `typesafe: unavailable`).

Unavailable or inconsistent required inputs produce a nonzero result with WHAT/WHY/HOW on **stderr**, not a partial prompt.

---

## Related documentation

- **[Installation Guide](../guides/installation-guide/README.md)** — step-by-step setup for new users.
- **[Activation Guide](../guides/activating-nwave-per-project.md)** — per-project activation workflow and opt-in/all mode concepts.
- **[Global Config Reference](./global-config.md)** — `~/.nwave/config.json` keys and schema.
- **[Outcomes CLI Reference](./outcomes-cli.md)** — outcomes registration and collision detection.
- **[nwdes command reference](../guides/nwdes/reference/index.md)** — the delivery CLI: roots, drafts, close and lane integration.
