# CLAUDE.md — nWave Developer Experience System

## What is nWave?

nWave is an AI-powered workflow framework that orchestrates specialized Claude AI agents through disciplined software development waves. It runs inside Claude Code, enforcing TDD, phase tracking, and deterministic validation at every step.

**Core mission**: Replace ad-hoc AI coding with a structured, auditable, wave-based methodology — from discovery to deployment.

**Two packages**:
- `nwave` (this repo, private) — development, full source, CI/CD
- `nwave-ai` (public, PyPI via `nwave-ai/nwave` repo) — installer CLI for end users

---

## Project Structure

```
nWave-dev/
├── nWave/                    # Framework definition (agents, commands, skills, templates)
│   ├── agents/               # 23 agent specifications (YAML frontmatter + markdown)
│   ├── tasks/nw/             # 21 slash command definitions (/nw:deliver, /nw:design, etc.)
│   ├── skills/               # 98 agent skill files (deep domain knowledge)
│   ├── templates/            # Methodology templates (TDD schema, pre-commit, README)
│   ├── data/                 # Configuration data, methodologies, research references
│   ├── hooks/                # Agent lifecycle hooks
│   ├── framework-catalog.yaml  # Central metadata registry (agents, commands, quality gates)
│   └── VERSION               # Framework version (synced from pyproject.toml)
│
├── src/des/                  # DES runtime (Deterministic Execution System)
│   ├── domain/               # Business logic (phase events, turn counter, timeout, policies)
│   ├── application/          # Use cases (orchestrator, validators, services)
│   ├── ports/                # Interfaces (driver + driven ports)
│   └── adapters/             # Implementations (hooks, filesystem, config, logging, git)
│
├── nwave_ai/                 # Public CLI package (thin wrapper)
│   └── cli.py                # Entry: install, uninstall, version commands
│
├── scripts/
│   ├── install/              # Installation pipeline
│   │   ├── plugins/          # Plugin system (agents, commands, DES, skills, templates, utilities)
│   │   ├── install_nwave.py  # Main installer orchestrator
│   │   ├── preflight_checker.py
│   │   └── installation_verifier.py
│   ├── hooks/                # Pre-commit hook scripts (all Python, zero shell)
│   ├── framework/            # Build utilities (sync names, create tarballs, docgen)
│   ├── validation/           # YAML & frontmatter validators
│   └── build_dist.py         # Distribution builder
│
├── tests/                    # 5-layer test suite
│   ├── des/                  # DES tests (unit/, integration/, acceptance/, e2e/)
│   ├── installer/            # Installer tests (unit/, acceptance/, e2e/)
│   ├── plugins/              # Plugin system tests
│   ├── bugs/                 # Regression tests
│   ├── build/                # Build script tests
│   └── conftest.py           # Root fixtures, auto-marking by directory
│
├── docs/
│   ├── guides/               # Tutorials and how-tos (public)
│   ├── reference/            # Auto-generated API/command reference (public)
│   ├── architecture/         # ADRs, design decisions (public)
│   └── analysis/             # Internal analysis (EXCLUDED from public sync)
│
├── .github/workflows/
│   ├── ci.yml                # 4-stage CI (lint → validate → test → sync)
│   └── release.yml           # 5-job release (bump → build → release → sync → pypi)
│
└── pyproject.toml            # Single source of truth for versions and tool config
```

---

## Architecture: DES (Deterministic Execution System)

DES follows **hexagonal architecture** (ports & adapters):

```
Claude Code Hooks (pre-tool-use, subagent-stop, post-tool-use)
        │
        ▼
┌─ Adapters (drivers) ──────────────────────────────────────┐
│  claude_code_hook_adapter.py  →  JSON hook protocol        │
└────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Application Layer ───────────────────────────────────────┐
│  DESOrchestrator       — prompt rendering, phase execution │
│  PreToolUseService     — validates before Task invocation  │
│  SubagentStopService   — validates after sub-agent returns │
│  TemplateValidator     — checks 9 mandatory sections       │
│  StaleExecutionDetector — detects abandoned phases         │
└────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Domain Layer ────────────────────────────────────────────┐
│  PhaseEvent, TurnCounter, TimeoutMonitor, TDDSchema       │
│  DES enforcement policies, Result<T,E> types              │
└────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Ports (driven) ──────────────────────────────────────────┐
│  FileSystemPort, ConfigPort, TimeProvider, AuditLogWriter  │
│  LoggingPort, TaskInvocationPort                           │
└────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Adapters (driven) ───────────────────────────────────────┐
│  RealFileSystem, EnvironmentConfigAdapter, SystemTimeProvider│
│  JsonlAuditLogWriter, GitCommitVerifier                    │
│  (+ in-memory/null variants for testing)                   │
└────────────────────────────────────────────────────────────┘
```

**TDD 5-Phase Cycle** (canonical, from `step-tdd-cycle-schema.json` v4.0):
1. PREPARE — setup test fixtures
2. RED_ACCEPTANCE — write failing acceptance test
3. RED_UNIT — write failing unit tests
4. GREEN — implement until all tests pass
5. COMMIT — refactor, finalize, no regressions

---

## Key Files (Quick Reference)

| File | Purpose |
|------|---------|
| `pyproject.toml` | Version, dependencies, tool config (THE source of truth) |
| `nWave/framework-catalog.yaml` | Agent/command/quality-gate registry |
| `nWave/VERSION` | Framework version (synced from pyproject.toml) |
| `src/des/application/orchestrator.py` | DES core orchestration (1,086 lines) |
| `src/des/adapters/drivers/hooks/claude_code_hook_adapter.py` | Hook entry point |
| `scripts/install/plugins/des_plugin.py` | DES installation plugin (core complexity) |
| `scripts/install/install_nwave.py` | Main installer orchestrator |
| `nwave_ai/cli.py` | Public CLI entry (`install`, `uninstall`, `version`) |
| `.releaserc` | Semantic-release config (branches, plugins) |
| `tests/conftest.py` | Root test config, auto-markers, fixtures |
| `scripts/docgen.py` | Documentation generator from frontmatter |

---

## Development Commands

```bash
# Testing
pipenv run pytest                          # All tests
pipenv run pytest tests/des/unit/          # DES unit tests only
pipenv run pytest -m unit                  # All unit tests
pipenv run pytest -m "not slow"            # Skip slow tests
pipenv run pytest --cov                    # With coverage (fail_under=60)

# Linting & Formatting
ruff check src/ scripts/ tests/            # Lint
ruff format .                              # Format (88 chars, double quotes)
mypy src/des/                              # Type check (strict mode)

# Pre-commit hooks
pre-commit run --all-files                 # All hooks
pre-commit run --hook-stage pre-push       # Push-time hooks only

# Build & Install
python scripts/build_dist.py               # Build distribution
python -m nwave_ai.cli install             # Install nWave locally

# Documentation
python scripts/docgen.py                   # Regenerate reference docs

# Mutation testing
pipenv run mutmut run                      # Run mutation tests
```

---

## Conventions

### Commits
- **Conventional commits required**: `type(scope): subject`
- Types: `feat` (minor), `fix`/`perf`/`refactor` (patch), `docs`/`test`/`ci`/`chore` (no release)
- `BREAKING CHANGE:` in body/footer triggers major bump
- Enforced by: gitlint (commit-msg hook) + commitlint (CI)

### Versioning (Two-Track)
- **nwave-dev** (this repo): semantic-release from conventional commits (`v2.17.5`)
- **nwave-ai** (public): auto-bumped patch from `public_version` floor in `[tool.nwave]` (`1.1.0`)

### Code Style
- Python >= 3.10, type hints everywhere (mypy strict)
- Ruff v0.15.0: line length 88, double quotes
- Naming: snake_case (functions/vars), PascalCase (classes), UPPER_SNAKE (constants)
- Docs: kebab-case filenames
- Zero shell scripts policy — all hooks in Python

### Testing (5-Layer Framework)
1. **Unit** — fast, isolated, one concern per test (pre-commit)
2. **Integration** — components with real resources (pre-push)
3. **Acceptance** — BDD Given-When-Then scenarios (pre-push)
4. **E2E** — complete workflows end-to-end (pre-push)
5. **Mutation** — test suite effectiveness validation (manual/CI)

Markers auto-applied by `conftest.py` based on directory path.

### Plugin System
Installation uses a plugin registry with topological dependency resolution:
- `base.py` — `InstallationPlugin` ABC, `InstallContext`, `PluginResult`
- Each plugin: `validate_prerequisites()` → `install()` → `verify()`
- DES plugin uses `$HOME` in hook commands for portability (never `.venv/` paths)
- Import rewriting: `from src.des` → `from des` at install time

---

## CI/CD Pipeline

### CI (`.github/workflows/ci.yml`) — Every push/PR
| Stage | Jobs | Duration |
|-------|------|----------|
| 1. Fast checks | commitlint, code-quality, file-quality, security | ~1 min |
| 2. Framework validation | catalog schema, version consistency, docs freshness | ~1 min |
| 3. Cross-platform tests | Ubuntu × Python 3.11/3.12 matrix | ~10 min |
| 4. Agent sync | Verify agent name synchronization | ~1 min |

### Release (`.github/workflows/release.yml`) — Manual dispatch or tag
1. **version-bump** — semantic-release calculates next version
2. **build** — `build_dist.py`, tarballs, SHA256SUMS
3. **github-release** — changelog from commits, GitHub Release + assets
4. **publish-to-nwave** — rsync to `nwave-ai/nwave`, auto-bump public version
5. **publish-to-pypi** — wheel build, twine publish, smoke test

Slack notifications on failure (RED) and recovery (GREEN).

---

## Wave Methodology

The canonical development sequence:

```
DISCOVER → DISCUSS → DESIGN → DEVOPS → DISTILL → DELIVER
```

| Wave | Command | Agent | Output |
|------|---------|-------|--------|
| DISCOVER | `/nw:discover` | product-discoverer | Evidence, opportunity validation |
| DISCUSS | `/nw:discuss` | product-owner | User stories, acceptance criteria |
| DESIGN | `/nw:design` | solution-architect | Architecture, component boundaries |
| DEVOPS | `/nw:devops` | platform-architect | Infrastructure, CI/CD, deployment |
| DISTILL | `/nw:distill` | acceptance-designer | BDD test scenarios (Given-When-Then) |
| DELIVER | `/nw:deliver` | software-crafter | Working code via Outside-In TDD |

**Cross-wave agents**: researcher, troubleshooter, documentarist, visual-architect
**Reviewers**: 11 peer review agents (one per specialist + specialized reviewers)

---

## Important Gotchas

- **Version source of truth**: `pyproject.toml:project.version` — everything else is synced
- **`docs/analysis/`**: Internal only, excluded from public repo sync via rsync rules
- **DES hook commands**: Use `$HOME` shell variable, never hardcoded paths
- **Pre-commit hooks**: Will block commits with failing tests, stale docs, or bad formatting
- **Plugin install rewrites imports**: `from src.des` becomes `from des` for standalone operation
- **No shell scripts**: Cross-platform policy enforced by pre-commit hook
- **Coverage threshold**: 60% minimum (will fail CI if below)
- **Ruff version pinned**: v0.15.0 — do not upgrade without updating CI and pre-commit
