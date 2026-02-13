# Contributing to nWave

## Development Setup

```bash
# Clone and install
git clone https://github.com/nWave-ai/nwave-dev.git
cd nwave-dev
pip install -e ".[dev]"

# Verify
pytest

# Install pre-commit hooks
pre-commit install
```

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
pytest

# Format code
ruff format .

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
