# Manual Setup: Tutorial 1 — Your First Delivery

If you'd rather run commands by hand instead of using `setup.py`, follow these steps. Run them from a directory where you want the tutorial project created (e.g. `~/projects` or `cd $(mktemp -d)`).

## 1. Create the project skeleton

```bash
mkdir -p tutorial-ascii-art/src/ascii_art tutorial-ascii-art/tests/fixtures
cd tutorial-ascii-art
touch src/__init__.py src/ascii_art/__init__.py tests/__init__.py
```

`src/ascii_art/__init__.py` is intentionally empty — that's the file nWave will fill in during delivery.

## 2. Create `pyproject.toml`

```bash
cat > pyproject.toml << 'EOF'
[project]
name = "ascii-art"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
EOF
```

## 3. Create `.gitignore`

```bash
cat > .gitignore << 'EOF'
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mutmut-cache/
docs/feature/
docs/evolution/
.nwave/
.develop-progress.json
EOF
```

## 4. Create the test fixture

A 4x4 PPM image with a white diagonal on a black background, used by all three tests.

```bash
cat > tests/fixtures/diagonal.ppm << 'EOF'
P3
4 4
255
255 255 255  0 0 0  0 0 0  0 0 0
0 0 0  255 255 255  0 0 0  0 0 0
0 0 0  0 0 0  255 255 255  0 0 0
0 0 0  0 0 0  0 0 0  255 255 255
EOF
```

## 5. Create the acceptance tests

These three tests define the complete feature contract. nWave will write the implementation to make them pass.

```python
# tests/test_ascii_art.py
"""Acceptance tests for image-to-ASCII converter.

These 3 tests define the complete feature contract.
nWave will implement the code to make them pass.
"""
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_converts_image_to_ascii_with_correct_width():
    """Given a PPM image
    When I convert it to ASCII art with width=20
    Then every line of output is exactly 20 characters wide."""
    from ascii_art import image_to_ascii

    result = image_to_ascii(FIXTURES / "diagonal.ppm", width=20)
    lines = result.strip().split("\n")

    assert len(lines) > 0
    assert all(len(line) == 20 for line in lines)


def test_output_uses_only_density_characters():
    """Given a PPM image
    When I convert it to ASCII art
    Then the output contains only characters from the density ramp."""
    from ascii_art import image_to_ascii

    DENSITY = " .:-=+*#%@"
    result = image_to_ascii(FIXTURES / "diagonal.ppm", width=10)

    for char in result:
        assert char in DENSITY or char == "\n"


def test_bright_pixels_produce_dense_characters():
    """Given an image with a white diagonal on black background
    When I convert it to ASCII art
    Then bright pixels map to dense characters like @ or #
    And dark pixels map to sparse characters like space or dot."""
    from ascii_art import image_to_ascii

    result = image_to_ascii(FIXTURES / "diagonal.ppm", width=4)
    lines = result.strip().split("\n")

    # The diagonal image has white pixels on the diagonal
    # First line: bright pixel at position 0, dark elsewhere
    first_line = lines[0]
    assert first_line[0] in "#%@"  # bright pixel -> dense char
    assert first_line[-1] in " .:"  # dark pixel -> sparse char
```

## 6. Create the virtualenv and install pytest

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
```

> **Windows users**: Replace `source .venv/bin/activate` with `.venv\Scripts\activate`.

## 7. Initialize git

nWave uses commits to track its TDD progress, so the project must be a git repo.

```bash
git init
git add -A
git commit -m "feat: ascii-art starter project (empty implementation, 3 failing tests)"
```

## Verify

You should now have:

- A `tutorial-ascii-art/` directory containing `src/ascii_art/__init__.py` (empty), `tests/test_ascii_art.py`, `tests/fixtures/diagonal.ppm`, `pyproject.toml`, and `.gitignore`
- A `.venv/` virtual environment with `pytest` installed
- A clean git repository with one initial commit
- Three failing acceptance tests (run `pytest tests/ -v` to confirm — they fail because `ascii_art.image_to_ascii` doesn't exist yet)

You're ready to start the tutorial.
