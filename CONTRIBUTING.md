# Contributing to nWave

Thank you for helping. This repository is the public face of nWave: framework
content (agents, skills, tasks, templates), the installer and the runtime that
ships in the `nwave-ai` wheel.

## Propose a change

1. Fork the repository and create a branch from `main`.
2. Make a focused change (one concern per pull request).
3. Open a pull request describing what changed and why. Maintainers review it,
   run it through their own checks, and carry accepted changes into the
   release line. Your authorship is preserved.

Commit messages follow the conventional format: `type(scope): subject`, for
example `fix(agents): correct the reviewer hand-off`. Keep the subject short and
lowercase after the prefix.

## Where things live

```text
.
├── nWave/                      # framework content: agents, skills, tasks, templates, data, schemas
├── nwave_ai/                   # installer and command-line entry point
├── src/                        # runtime packages shipped in the wheel (nwdes, codefact, nwave_capture)
├── scripts/install/            # installation scripts
├── docs/guides/                # tutorials and how-to guides
├── docs/reference/             # generated reference (agents, skills, commands, templates)
└── pyproject.toml              # packaging
```

`docs/reference/` is generated from the content under `nWave/`: change the
source and describe the change in your pull request; do not hand-edit the
generated pages.

## Set up

```bash
git clone https://github.com/nWave-ai/nWave.git
cd nWave
uv sync
```

Python 3.11 or newer is required. To try your change against a real project,
install your checkout in a scratch environment and run the installer from
there; see `docs/guides/installation-guide/` and `docs/guides/offline-install.md`.

## Commit identity

Set your git identity before the first commit and tell git never to guess one:

```bash
git config --global user.name "<your-name>"
git config --global user.email "<your-email-or-github-noreply-address>"
git config --global user.useConfigOnly true
```

Placeholder or malformed author and committer addresses (for example
`test@example.com`, `*.local`) are rejected by maintainers' checks. GitHub
no-reply addresses are fine.

## Principles

1. Each agent has one responsibility.
2. Agents communicate through file-based handoffs (JSON or YAML).
3. A behavioural change is described with the scenario it affects, so reviewers
   can reproduce it.

## Reporting problems

Open an issue with the nWave version (`nwave-ai --version`), your operating
system, the agent or command involved, and what you expected instead.
