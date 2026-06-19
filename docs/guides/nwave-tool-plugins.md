# nWave Tool Plugins — Develop & Install

This guide covers **nWave tool plugins**: standalone Python CLIs that extend
nWave's capabilities (scanning, analysis, generation) and live as separate
PyPI packages under the `nWave-ai` GitHub organization.

> **Not the same as Claude Code plugins.** The
> [`plugin-migration-guide`](plugin-migration-guide/) covers the Claude Code
> plugin (`claude plugin install nw`), which is an alternative install method
> for the nWave methodology itself. Tool plugins are independent CLIs you
> compose with nWave (or use standalone).

---

## What is a tool plugin?

A nWave tool plugin is a Python package that:

1. Lives in its own GitHub repo under `nWave-ai/` (e.g. `nWave-ai/nwave-dedup`)
2. Ships its own PyPI wheel installable via `uv tool`, `pipx`, or `pip`
3. Exposes a CLI named `nwave-<verb>` (e.g. `nwave-dedup`, `nwave-audit`)
4. Has its own version, tests, CI, and release cadence — independent of
   `nwave-ai` core
5. Can be invoked from the command line OR from inside nWave waves

The first reference implementation is
[`nWave-ai/nwave-dedup`](https://github.com/nWave-ai/nwave-dedup) — a
cross-language duplicate-shape scanner.

## Why tool plugins exist

The `nwave-ai` PyPI wheel is intentionally a thin installer (it ships only
agents, commands, skills, and the DES runtime). Heavyweight tooling — AST
parsing, security scanning, doc generators — would bloat the wheel and
couple tool releases to methodology releases.

Tool plugins solve this by:

- Letting tools ship at their own pace (a scanner bug-fix doesn't need a
  methodology release)
- Letting users install only what they need (`uv tool install nwave-dedup`
  doesn't pull tree-sitter grammars unless they want them)
- Letting external contributors own a tool without touching the
  methodology core

## Naming + structure conventions

Adopting these conventions makes a tool discoverable as part of the nWave
ecosystem.

| Aspect              | Convention                                                |
|---------------------|-----------------------------------------------------------|
| GitHub repo         | `nWave-ai/nwave-<verb>` (lowercase, hyphenated)          |
| PyPI package        | `nwave-<verb>`                                           |
| Python module       | `nwave_<verb>` (snake-case for import compat)            |
| CLI entry point     | `nwave-<verb>` (matches PyPI name)                       |
| License             | MIT (matches `nwave-ai`)                                 |
| Python target       | `>=3.10` (matches `nwave-ai` minimum)                    |
| Build backend       | `hatchling>=1.20` (recommended; consistent with `nwave-ai`) |
| Pre-alpha versions  | `0.1.0.dev0` style — signal stability honestly           |

### Recommended repo layout

```
nwave-<verb>/
├── pyproject.toml          # hatchling, dependencies, [project.scripts]
├── README.md               # what / why / install / usage / limitations
├── LICENSE                 # MIT
├── .github/workflows/
│   └── ci.yml              # ruff + pytest matrix Py3.10/3.11/3.12
├── src/
│   └── nwave_<verb>/
│       ├── __init__.py     # __version__ = "..."
│       ├── cli.py          # entry point; argparse-based
│       └── ...             # domain modules
└── tests/
    └── test_*.py
```

The `src/` layout (rather than flat) is recommended because it prevents
test-time import shadowing and matches `nwave-ai` itself.

## Develop your first plugin (5 steps)

### 1. Scaffold the repo

```bash
mkdir nwave-myverb && cd nwave-myverb
git init
gh repo create nWave-ai/nwave-myverb --public --source . --description "..."
```

### 2. Write `pyproject.toml`

Reference the [nwave-dedup pyproject.toml](https://github.com/nWave-ai/nwave-dedup/blob/main/pyproject.toml)
as a starting template. Key fields:

```toml
[project]
name = "nwave-myverb"
version = "0.1.0.dev0"
requires-python = ">=3.10"

[project.scripts]
nwave-myverb = "nwave_myverb.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/nwave_myverb"]
```

### 3. Implement the CLI

Use `argparse` (no extra deps required). Always provide:

- `--version` (reads `__version__` from your package)
- A subcommand structure (`nwave-myverb scan`, `nwave-myverb fix`, etc.) —
  even if you ship only one subcommand initially, the structure is
  forward-compatible

### 4. Write tests + CI

Minimum: smoke tests for the public API + a GitHub Actions matrix CI.
Reference the [nwave-dedup CI workflow](https://github.com/nWave-ai/nwave-dedup/blob/main/.github/workflows/ci.yml).

### 5. Publish

For pre-alpha (`0.x.dev0`): users install via git URL, no PyPI publish needed:

```bash
pip install git+https://github.com/nWave-ai/nwave-myverb.git
```

For first stable (`0.1.0` or `1.0.0`):

```bash
# Build
python -m build

# Upload (requires PyPI maintainer access on the nwave-ai org)
twine upload dist/*
```

## Install a plugin (end-user)

Three options, in order of preference:

### Option 1 — `nwave-ai plugin install` (recommended)

If you already have `nwave-ai` installed, the integrated subcommand
discovers known plugins from a built-in registry and installs them via
the same toolchain that owns nwave-ai (uv → pipx → pip priority).
Override with `NWAVE_INSTALLER=uv` or `NWAVE_INSTALLER=pipx` if needed:

```bash
nwave-ai plugin install dedup
# Resolves "dedup" → "nwave-dedup".
# Runs `uv tool install nwave-dedup` (or `pipx install nwave-dedup`
# if nwave-ai itself is pipx-installed). Verifies the CLI is on PATH.
```

List known plugins:

```bash
nwave-ai plugin list
# dedup    nwave-dedup
```

Uninstall:

```bash
nwave-ai plugin uninstall dedup
```

### Option 2 — Direct install (no nwave-ai required)

Tool plugins are independent PyPI packages — install one without
installing `nwave-ai` at all:

```bash
uv tool install nwave-dedup    # recommended
# or, as a fallback:
pipx install nwave-dedup
# or:
pip install nwave-dedup
```

### Option 3 — Pre-release / git URL

For pre-release versions or unreleased branches:

```bash
uv tool install git+https://github.com/nWave-ai/nwave-dedup.git
# or:
pipx install git+https://github.com/nWave-ai/nwave-dedup.git
```

### Verify

```bash
nwave-dedup --version
# nwave-dedup 0.1.0.dev0
```

## Compose plugins with nWave waves

A tool plugin can be invoked from any nWave wave via shell. Example: have
the `software-crafter` agent run `nwave-dedup scan` after each L3 refactor:

```yaml
# In a custom skill or wave config
post_refactor_check:
  - run: nwave-dedup scan src/ --format json --output /tmp/dup.json
  - assert: jq '.total_groups' /tmp/dup.json | xargs test 0 -ge
```

This is composition, not coupling — the plugin doesn't know about nWave;
nWave just shells out to it.

## Discoverability

Once published, list your plugin in the [nWave marketplace](../marketplace/)
so users can find it. (Marketplace registration TBD as more plugins ship.)

## Honest limitations of the current design

- **No discovery API.** Users find plugins via the marketplace doc, not via
  `nwave plugin list`. A registry CLI is a v2 nWave-ai feature, not yet
  shipped.
- **No version compatibility check.** A plugin doesn't declare which
  `nwave-ai` core version it expects. For now, plugins are pinned to public
  CLI surfaces (e.g. shell composition); they don't import nWave internals.
- **No plugin sandbox.** A plugin runs with the same privileges as the user.
  If you install a plugin from outside `nWave-ai/`, audit the source first.

## See also

- [`nwave-dedup`](https://github.com/nWave-ai/nwave-dedup) — first reference plugin
- [`plugin-migration-guide/`](plugin-migration-guide/) — migrating to the **Claude Code** plugin (different concept)
- [`installation-guide/`](installation-guide/) — installing `nwave-ai` core
