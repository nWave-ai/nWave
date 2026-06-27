# Contributing to nWave

## Development Setup

```bash
# Clone and install (uv installs the project + dev group from uv.lock)
git clone https://github.com/nWave-ai/nwave-dev.git
cd nwave-dev
uv sync

# Install pre-commit hooks (all types: pre-commit, pre-push, commit-msg, ...)
uv run poe install-hooks

# Install flock — REQUIRED by the pre-commit/pre-push test hooks (see
# "Prerequisite: flock" below). Do this BEFORE the first commit/test run.
#   macOS:          brew install flock
#   Debian/Ubuntu:  sudo apt install util-linux   # usually already installed
#   Fedora/RHEL:    sudo dnf install util-linux    # usually already installed
flock --version    # confirm it is on PATH

# Verify
uv run poe test
```

> Don't have uv? `curl -LsSf https://astral.sh/uv/install.sh | sh` (see [uv docs](https://docs.astral.sh/uv/getting-started/installation/)).

### Prerequisite: `flock`

The pre-commit and pre-push hooks wrap every pytest run in `flock` so concurrent
runs (e.g. an overlapping commit and push) can't corrupt `.git/` — the suite
serialises on a single lock (`flock -w 1800 /tmp/nwave-pytest.lock …`, see
`.pre-commit-config.yaml`). If `flock` isn't on your `PATH`, the hooks fail
immediately with `flock: command not found`, so install it up front — don't
leave it to be discovered after a long test wait.

| OS | Install |
|----|---------|
| macOS | `brew install flock` (the [discoteq](https://github.com/discoteq/flock) formula — macOS has no `flock` otherwise) |
| Debian / Ubuntu | `sudo apt install util-linux` (ships `flock`; usually already present) |
| Fedora / RHEL | `sudo dnf install util-linux` (ships `flock`; usually already present) |
| Windows | Run the hooks under **WSL** (recommended) or an MSYS2 / Cygwin shell — `flock` comes with `util-linux` there; native PowerShell / CMD don't provide it |

Confirm with `flock --version`.

### Prerequisite: commit identity

Set your git identity before the first commit, and tell git never to guess one:

```bash
git config --global user.name "<your-name>"            # replace with YOUR real name
git config --global user.email "<your-email>"          # replace with YOUR real email, or a GitHub no-reply address
git config --global user.useConfigOnly true            # one-time: never guess user@hostname
```

`user.useConfigOnly true` (git 2.8+) stops git from inventing a
`you@your-machine.local` identity when `user.email` is unset — the most common
way a misconfigured identity slips into history. It is **preventive**: the commit
fails loudly instead of being created with a guessed identity.

This pairs with the identity gates the hooks enforce (and CI re-enforces): a
commit or push is **refused** if its author *or* committer email is a known
placeholder (`test@example.com`, `t@t.com`), a reserved/placeholder domain
(`example.com`, `test.com`, `localhost`, `*.local`), empty, or malformed.
Legitimate anonymous GitHub addresses (`*@users.noreply.github.com`) are always
allowed. If a commit is rejected, fix the identity with the `git config` commands
above and re-commit — the gate names which field (author/committer) was rejected.

## Pre-commit Hooks

Hooks run automatically on every commit:

- Python linting and formatting (ruff)
- YAML syntax validation
- Test execution
- Trailing whitespace removal

For emergency bypass (not recommended):

```bash
git commit --no-verify
```

## Making Changes

```bash
# Run tests
uv run poe test

# Format code
uv run poe format

# Commit with conventional format
git commit -m "feat(agents): add new capability"
```

## Architecture Principles

1. Each agent has one responsibility
2. Agents communicate through file-based handoffs (JSON/YAML)
3. All behavioral changes ship with tests
4. Quality gates enforce standards at every commit

## Project Structure

```text
.
├── src/des/                    # DES runtime module
├── scripts/
│   ├── install/               # Installation scripts and CLI
│   │   └── plugins/           # Plugin system (agents, commands, DES, etc.)
│   └── utils/                 # Utility scripts
├── docs/
│   ├── guides/                # Tutorials and how-to guides
│   └── reference/             # API and command reference
├── tests/                     # Automated test suite
├── .pre-commit-config.yaml    # Quality gates
└── pyproject.toml             # Project configuration
```
