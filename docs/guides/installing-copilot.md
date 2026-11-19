# Installing nWave for GitHub Copilot (terminal and VS Code)

## Goal

After this guide, you can use nWave from the terminal in the GitHub Copilot CLI (`copilot`), and the same files are
read by the Copilot harness of VS Code chat. The personal install
puts nWave's public roles, skills and hooks under `~/.copilot` (or `$COPILOT_HOME`). The project install puts the
same roles and skills, and one prompt file per wave, under the project's `.github` folders, when you choose it.

Each result below names its receipt. The model-session receipts and the earlier delivery's receipts are not published:
the records behind them stay in the project's research folder, so this guide states each observation with its limits
and links to none of them. Anything without a receipt is marked as a repository check, not as a session.

## Prerequisites

- **Python 3.11 or later**, and **uv** or **pipx**, as in the other host guides.
- **GitHub Copilot CLI** (`copilot`), signed in with your GitHub account (`copilot login`, or a token in
  `GH_TOKEN`).

## Install

### Step 1: Install the nWave CLI

```bash
uv tool install nwave-ai     # recommended
# or
pipx install nwave-ai
```

### Step 2: Install for Copilot

```bash
nwave-ai install --platform copilot --yes
```

The install writes:

| Where | What | Count (install report) |
|---|---|---|
| `~/.copilot/agents/nw-<role>.agent.md` | Public roles as custom agents, name and description in the frontmatter | 37 agents |
| `~/.copilot/skills/nw-<name>/SKILL.md` | Public skills, the same selection as the Claude install | 187 skills |
| `~/.copilot/hooks/nwave-hooks.json` | nWave's hook registration (see Hooks below) | 1 file |

The install report says what it wrote and that it did not check whether the CLI loads the files. Only a session
shows that. Run the install again and it changes nothing (see Update and uninstall).

## Use nWave from the terminal

### Roles

Copilot has no custom slash command for nWave roles. A role is reached with `--agent`. The four runs that were
recorded used this command, with the three-check prompt:

```bash
copilot --agent nw-nwave-buddy --model auto --allow-all-tools --no-auto-update --output-format json \
  -p "Answer three checks, one line each, quoting evidence. 1) Who are you? State your role in one sentence. 2) Without running any tool, describe the nwdes skill in one sentence and name the folder it was loaded from. 3) Run the shell command nwdes --help and quote its first output line exactly."
```

Recorded results (receipts role-1 to role-4):

- **Answered as the role in 3 of 4 runs.** Those answers named Guide, the nWave Concierge. The fourth answered as the
  default Copilot CLI.
- The role's text reached the request in all four runs, and the debug log printed `skipping custom agents load` in all
  four.

For the same command in the earlier delivery (receipts in the t-0467 evidence file), run 4 answered as the role and
run 6 did not. Across those six runs, four answered as the role. That is not a rate.

Without `--model auto`, the earlier delivery's runs 1 and 2 answered as the default CLI, so keep `--model auto`.
Interactive mode (`/agent`) was not tried.

### Waves and skills

nWave's wave entry points are the files in `nWave/tasks/nw`. Every public wave has a public skill, so a Copilot user
reaches each one by its skill name. The repository check that lists these skills is the only evidence for the table,
and the session below is the only receipt for a wave.

| Wave | Skill name | Source of the skill |
|---|---|---|
| buddy | `nw-buddy` | `nWave/skills` |
| bugfix | `nw-bugfix` | `nWave/skills` |
| deliver | `nw-deliver` | `nWave/skills` |
| design | `nw-design` | `nWave/skills` |
| devops | `nw-devops` | `nWave/skills` |
| diagram | `nw-diagram` | `nWave/skills` |
| discover | `nw-discover` | `nWave/skills` |
| discuss | `nw-discuss` | `nWave/skills` |
| distill | `nw-distill` | `nWave/skills` |
| diverge | `nw-diverge` | `nWave/skills` |
| document | `nw-document` | `nWave/skills` |
| forge | `nw-forge` | `nWave/skills` |
| hotspot | `nw-hotspot` | `nWave/skills` |
| mikado | `nw-mikado` | `nWave/skills` |
| mode-select | `nw-mode-select` | `nWave/skills` |
| mutation-test | `nw-mutation-test` | `nWave/skills` |
| optimize-tests | `nw-optimize-tests` | `nWave/skills` |
| refactor | `nw-refactor` | `nWave/skills` |
| research | `nw-research` | `nWave/skills` |
| review | `nw-review` | `nWave/skills` |
| root-why | `nw-root-why` | `nWave/skills` |
| spike | `nw-spike` | `nWave/skills` |

Receipt wave-r5: in a real session, the prompt "Use the skill tool to load the skill named nw-discuss, then quote the
first markdown heading" made the skill tool load `nw-discuss`, and the answer quoted `# Discuss: from request to
agreed product facts`.

### Project instructions

The Copilot CLI reads these repository instruction files. Receipt local-commands shows `copilot instruction list`
listing `AGENTS.md` and `CLAUDE.md` in one folder, and `.github/copilot-instructions.md` in another.

The nWave project section is written into `CLAUDE.md` and `AGENTS.md` by `nwave-ai project enable --yes`. The
personal and project Copilot installs do not write it.

Receipt instr-r6: the model quoted the first sentence of the nWave section, `Three routes are open to a Request:`,
and named `AGENTS.md`. The same section is in `CLAUDE.md`.

### Hooks

The hook file `~/.copilot/hooks/nwave-hooks.json` declares `"version": 1` (the hook format version every documented
Copilot hook file carries) and one event, `preToolUse`, with the matcher `.*`. It runs
`python -m nwave_ai.hooks PreToolUse --host copilot`. No other event is declared for Copilot.

**One-time change (card t-0559).** Earlier installs wrote this file without `"version"`. The install that carries this
change adds `"version": 1` to that file, once. It repairs the file in place: another tool's entries are kept, a reinstall
writes the same bytes, and a file that declares a version other than 1 is refused with what, why and how, and its bytes
are left unchanged. Nothing else the CLI install writes changes bytes.

The guard acts on the two shell tool names the GitHub hooks reference lists under "Tool names for hook matching":
`bash` (Unix) and `powershell` (Windows). It reads the command text from `command`, then `cmd`, and reads arguments that
arrive as JSON text. A call whose command it cannot read is allowed. The argument shape of a `powershell` call is not
documented in the reference, so the `cmd` key and the rule that an unreadable call is allowed are the tested behaviour;
the live shape is the P5 observation the root runs (see the VS Code section).

Recorded results:

- **The hook receives the bash calls.** Receipt hookprobe: a scratch hook recorded the payload Copilot sent for one bash
  call. It holds `toolName` (`bash`) and `toolArgs` (an object with `command`). The later receipts show the same hook
  acting on bash calls.
- **Before the Copilot adapter, a stash ran.** Receipt hook-r7: the handler read Claude's `tool_name` and
  `tool_input`, so it never saw the Copilot bash call. `git stash push -m probe` ran, and the stash list grew.
- **With the Copilot adapter, the stash was refused, then bypassed.** Receipt hookfix: the hook printed
  `permissionDecision: deny`, and the tool result read `Denied by preToolUse hook: git stash is forbidden`. The model's
  next call ran `NWAVE_GIT_STASH_ALLOW=1 git stash push`, the audited bypass that the refusal message names, and the
  stash was created.
- **An ordinary call is allowed.** A bash call such as `echo ok` gets exit 0 and empty output. This is observed by the
  repository test `test_copilot_denies_a_stash_call_and_lets_an_ordinary_bash_call_through`, not by a session.

Notes:

- Only the git-stash guard acts for Copilot. The other kept handlers still read Claude's envelope and do not act for
  Copilot.
- A bypass written to the audit record for a Copilot call has an empty `session_id`: the adapter does not pass the
  Copilot session id to the stash guard.
- The hook command imports `nwave_ai` from the Python environment it runs in. Receipt hookfix set `PYTHONPATH` to a
  checkout, and receipt hook-r7 did not; so the code a session runs depends on the environment it starts in.

### Project level: `.github/agents`, `.github/skills` and prompt files

The project install is a choice. Nothing is written into a project until you run:

```bash
nwave-ai project copilot enable --yes     # writes into this project's .github folders
nwave-ai project copilot disable          # removes only what enable wrote
```

`enable` without `--yes` writes nothing and says why. It writes:

- `.github/agents/nw-<role>.agent.md` for each public role (37);
- `.github/skills/nw-<name>/` for each public skill;
- `.github/prompts/nw-<wave>.prompt.md` for each wave entry point (23), with the wave's description.

It refuses before writing anything if a file at one of those names was not written by nWave, and it names that file.
A second `enable` writes the same bytes. `disable` removes the files its manifests list and keeps your own files.

Receipt proj-r8: in a fresh Copilot home with no nWave files, a project with the `.github` folders loaded the skill
`nw-discuss` from the project, and the session answered as the role Guide.

**Prompt files: not loaded in the observed runs.**

- Receipt prompt-r9: asked to look for `nw-discuss.prompt.md`, the model read the file only because it was asked.
- Receipt prompt-slash: `/nw-discuss` was sent as the prompt. The session listed the project folder, loaded the skill
  `nw-discuss` through the skill tool, and did not open a prompt file.

The project install still writes these files, for the hosts that read them. They are **Local-harness only**: the Copilot
harness (the terminal and VS Code chat) does not load `*.prompt.md` files, and the vendor says so. The Local harness is
deprecated and is removed in February 2027. Use the wave's skill (`nw-<wave>`) in Copilot; the prompt file is kept for
the Local harness until then. Visual Studio reading these files is reported by the request, not tested here.

## VS Code chat (Copilot harness): documented, not observed in VS Code

Status: **documented, not observed in VS Code.** Nothing in this section has been run in a VS Code chat session. The
observation protocol is `docs/feature/copilot-chat-in-vscode/runbook.md`; the owner runs it with a live GitHub sign-in.
Until its results are recorded, read this section as documentation.

The same install serves VS Code chat. VS Code has no separate install step: the Copilot harness that VS Code runs reads
the personal folders this guide already names. Status of each claim is stated separately.

**Documented (the vendor pages and the GitHub Copilot hooks reference, read 18 November 2026):**

- Personal custom agents in `~/.copilot/agents` and skills in `~/.copilot/skills`; personal hooks in `~/.copilot/hooks/`
  (or `$COPILOT_HOME/hooks/`). Project customizations in `.github/agents`, `.github/skills`, `.github/hooks`.
- Hook files use `"version": 1`; `preToolUse` receives `toolName` and `toolArgs`; the shell tool names are `bash` and
  `powershell`; a `preToolUse` command that returns `permissionDecision: deny` refuses the call.
- Prompt files are not loaded by the Copilot harness.

**Observed on this machine:** the install writes these folders (the install report and the files, read back). No VS Code
chat session has been run by this repository.

**Unobserved until a person runs the protocol:** that VS Code discovers the agents, skills and hooks above; that a skill
loads in a chat; that the guard denies a `git stash` call sent by VS Code chat, with the `bash` and the `powershell` tool
names; and the payload shape of a `powershell` call. The check that observes them is the runbook
`docs/feature/copilot-chat-in-vscode/runbook.md` (P0 to P7), which the owner runs with a live sign-in.

Until those results are recorded, read this section as documentation, not as an observed result.

## Update and uninstall

- **Personal install:** `nwave-ai install --platform copilot --yes` again replaces only what nWave wrote. A file of
  your own at a role name is refused, and the install writes nothing before it refuses.
- **Project install:** run `nwave-ai project copilot enable --yes` again to update it. `nwave-ai project copilot
  disable` removes only the files listed in the three manifests.

Receipt local-commands (isolated home, no model call):

- A second `nwave-ai install --platform copilot --yes` left all 232 files under `agents`, `skills` and `hooks` with the
  same bytes. Its report said 37 agents and 187 skills were installed.
- Three files of the user's own were placed in the same folders, then `nwave-ai uninstall --force` ran. All three kept
  their bytes. The report named the removal of the 37 agents, the 187 skills and the kept hook registrations.

## Not tested

- **VS Code chat is documented, not observed.** The VS Code pages and the GitHub Copilot hooks reference name the same
  personal folders the terminal install writes. Nothing in a VS Code chat session has been run by this repository. The
  observation is the runbook `docs/feature/copilot-chat-in-vscode/runbook.md`; until a person records its results, the
  claim stays "documented, not observed in VS Code".
- **Visual Studio is not tested and out of scope.** Its hooks are not supported (per the GitHub cheat sheet), so no guard
  applies there.
- Interactive mode and `/agent` were not tried.
- Role adoption is not a rate: 3 of 4 is the recorded result of one command.
- The project-level session receipt covers one fresh home. Other project layouts were not run.

## Verify

```bash
copilot instruction list     # which instruction files the CLI reads
copilot skill list           # the personal and project skills the CLI sees
```

## Next steps

- [Vendor support](vendor-support.md): what each host receives and how deeply it is verified.
- [Installation guide](installation-guide/): the Claude Code install.
