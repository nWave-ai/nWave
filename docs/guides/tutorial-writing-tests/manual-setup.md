# Manual Setup: Tutorial 2 — Writing Acceptance Tests

If you'd rather run commands by hand instead of using `setup.py`, follow these steps. Run them from a directory where you want the tutorial project created (e.g. `~/projects` or `cd $(mktemp -d)`).

## 1. Create the project skeleton

```bash
mkdir -p md-converter/src/md_converter md-converter/tests
cd md-converter
touch src/md_converter/__init__.py tests/__init__.py
```

## 2. Create `pyproject.toml`

```bash
cat > pyproject.toml << 'EOF'
[project]
name = "md-converter"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
EOF
```

## 3. Create the virtualenv and install pytest

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
```

> **Windows users**: Replace `source .venv/bin/activate` with `.venv\Scripts\activate`.

## 4. Initialize git

nWave uses commits to track its TDD progress, so the project must be a git repo.

```bash
echo ".venv/" > .gitignore
git init
git add -A
git commit -m "chore: initial project structure"
```

## Verify

You should now have:

- A `md-converter/` directory with `src/md_converter/__init__.py`, `tests/__init__.py`, `pyproject.toml`, and `.gitignore`
- A `.venv/` virtual environment with `pytest` installed
- A clean git repository with one initial commit

You're ready to start writing your first acceptance test.
