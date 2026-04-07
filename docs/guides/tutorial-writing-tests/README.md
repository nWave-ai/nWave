# Tutorial: Writing Acceptance Tests That Guide Delivery

**Time**: ~15 minutes (6 steps)
**Platform**: macOS or Linux (Windows: use WSL)
**Prerequisites**: Python 3.10+, Claude Code with nWave installed, [Tutorial 1](../tutorial-first-delivery/) completed
**Dependencies**: None beyond pytest. Pure Python.

---

## What You'll Build

A Markdown-to-HTML converter — built entirely from tests you write yourself.

**Before** — raw Markdown:

```markdown
# Hello World

This is **bold** and this is *italic*.

- Item one
- Item two
```

**After** — your `markdown_to_html()` function produces:

```html
<h1>Hello World</h1>
<p>This is <strong>bold</strong> and this is <em>italic</em>.</p>
<ul>
<li>Item one</li>
<li>Item two</li>
</ul>
```

In Tutorial 1, the tests were written for you. This time, **you** write them. This is the core skill: define "done" precisely, then let nWave build it. Good tests are the difference between code that works and code that merely compiles.

---

## Step 1 of 6: Create the Project (~2 minutes)

This time there's no starter repo — you build from scratch.

```bash
mkdir md-converter && cd md-converter
python3 -m venv .venv && source .venv/bin/activate
pip install pytest
```

You should see:

```
Successfully installed pytest-x.x.x
```

> **Windows users**: Replace `source .venv/bin/activate` with `.venv\Scripts\activate`.

Now create the project structure:

```bash
mkdir -p src/md_converter tests
touch src/md_converter/__init__.py tests/__init__.py
```

Create `pyproject.toml`:

```bash
cat > pyproject.toml << 'EOF'
[project]
name = "md-converter"
version = "0.1.0"
requires-python = ">=3.10"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
EOF
```

Verify the structure:

```bash
find . -not -path './.venv/*' -not -path './.venv' | sort
```

```
.
./pyproject.toml
./src
./src/md_converter
./src/md_converter/__init__.py
./tests
./tests/__init__.py
```

> **If `find` output differs slightly**: As long as you have `src/md_converter/__init__.py`, `tests/__init__.py`, and `pyproject.toml`, you're good.

Initialize git (nWave uses commits to track its TDD progress):

```bash
git init && git add -A && git commit -m "chore: initial project structure"
```

You should see:

```
[main (root-commit) ...] chore: initial project structure
```

*Next: you'll write your first acceptance test — the simplest possible behavior.*

---

## Step 2 of 6: Write Your First Test — The Simplest Behavior (~2 minutes)

Here's the key principle: **start with the simplest test, then add complexity**. This is the density ramp — the same idea as learning to walk before you run.

Your first test should define the most basic thing the converter does: turn a heading into HTML.

Create `tests/test_markdown.py`:

```python
# tests/test_markdown.py
from md_converter import markdown_to_html


def test_converts_heading_to_html():
    """A line starting with # becomes an <h1> tag."""
    result = markdown_to_html("# Hello World")
    assert result.strip() == "<h1>Hello World</h1>"
```

Notice three things about this test:

1. **The name reads as a specification**: `test_converts_heading_to_html` — anyone can tell what the feature does
2. **It tests behavior, not implementation**: we don't say "use regex" or "split the string" — just what goes in and what comes out
3. **It's tiny**: one input, one output, one assertion

Run it to confirm it fails:

```bash
pytest tests/ -v
```

```
FAILED tests/test_markdown.py::test_converts_heading_to_html - ImportError

1 failed
```

Red. Good. That failing test is your specification — it defines one behavior you want.

> **If you see `ModuleNotFoundError` instead of `ImportError`**: Both mean the same thing — the function doesn't exist yet. Your test is working correctly.

*Next: you'll add tests for bold/italic — defining how inline formatting works.*

---

## Step 3 of 6: Add Inline Formatting Tests (~3 minutes)

Now add a second behavior: bold and italic text. This is slightly more complex because it handles *inline* formatting rather than whole lines.

Add this test to `tests/test_markdown.py` (below the existing test):

```python
def test_converts_bold_and_italic_text():
    """Double asterisks become <strong>, single become <em>."""
    result = markdown_to_html("This is **bold** and *italic* text.")
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result
```

Why `in` instead of `==`? Because we're testing the **bold/italic behavior** specifically. We don't care whether the surrounding text is wrapped in `<p>` tags yet — that would test two things at once. Keep tests focused on one behavior.

Now add an edge case. Edge cases define boundaries — they're where bugs hide:

```python
def test_plain_text_returns_as_paragraph():
    """Text with no Markdown syntax wraps in a <p> tag."""
    result = markdown_to_html("Just plain text.")
    assert result.strip() == "<p>Just plain text.</p>"
```

This test answers: "What happens when there's *no* Markdown?" That boundary matters — it prevents the converter from mangling regular text.

Run the tests:

```bash
pytest tests/ -v
```

```
FAILED tests/test_markdown.py::test_converts_heading_to_html
FAILED tests/test_markdown.py::test_converts_bold_and_italic_text
FAILED tests/test_markdown.py::test_plain_text_returns_as_paragraph

3 failed
```

Three red tests, three behaviors specified. Each test name reads like a requirement:

1. Converts headings to HTML
2. Converts bold and italic text
3. Wraps plain text in paragraphs

*Next: you'll add one more test for lists, completing your specification.*

---

## Step 4 of 6: Add a List Conversion Test (~2 minutes)

The final behavior: unordered lists. Lines starting with `- ` become list items.

Add this to `tests/test_markdown.py`:

```python
def test_converts_unordered_list():
    """Lines starting with '- ' become <ul> with <li> items."""
    markdown = "- First\n- Second\n- Third"
    result = markdown_to_html(markdown)
    assert "<ul>" in result
    assert "<li>First</li>" in result
    assert "<li>Second</li>" in result
    assert "<li>Third</li>" in result
    assert "</ul>" in result
```

Run all four tests:

```bash
pytest tests/ -v
```

```
FAILED tests/test_markdown.py::test_converts_heading_to_html
FAILED tests/test_markdown.py::test_converts_bold_and_italic_text
FAILED tests/test_markdown.py::test_plain_text_returns_as_paragraph
FAILED tests/test_markdown.py::test_converts_unordered_list

4 failed
```

Four red tests. Let's look at what you've built — your complete test file should look like this:

```python
# tests/test_markdown.py
from md_converter import markdown_to_html


def test_converts_heading_to_html():
    """A line starting with # becomes an <h1> tag."""
    result = markdown_to_html("# Hello World")
    assert result.strip() == "<h1>Hello World</h1>"


def test_converts_bold_and_italic_text():
    """Double asterisks become <strong>, single become <em>."""
    result = markdown_to_html("This is **bold** and *italic* text.")
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result


def test_plain_text_returns_as_paragraph():
    """Text with no Markdown syntax wraps in a <p> tag."""
    result = markdown_to_html("Just plain text.")
    assert result.strip() == "<p>Just plain text.</p>"


def test_converts_unordered_list():
    """Lines starting with '- ' become <ul> with <li> items."""
    markdown = "- First\n- Second\n- Third"
    result = markdown_to_html(markdown)
    assert "<ul>" in result
    assert "<li>First</li>" in result
    assert "<li>Second</li>" in result
    assert "<li>Third</li>" in result
    assert "</ul>" in result
```

Read these test names aloud. They're a specification:

- Converts heading to HTML
- Converts bold and italic text
- Wraps plain text as paragraphs
- Converts unordered lists

That's what "done" looks like. You didn't describe *how* to parse Markdown. You described *what correct output looks like* for each case.

Commit your tests before handing off to nWave:

```bash
git add -A && git commit -m "test: acceptance tests for markdown-to-html converter"
```

*Next: you'll hand these tests to nWave and watch it build the implementation.*

---

## Step 5 of 6: Let nWave Deliver (~5 minutes)

> **AI output varies between runs.** Your code will differ from the examples
> below. That is normal. We define success by what the code *does* (tests pass),
> not what the agent *says*.

Open Claude Code and start the delivery:

```bash
claude
```

Then type this Claude Code command (not a terminal command):

```
/nw-deliver "Markdown-to-HTML converter"
```

This takes 3-5 minutes. You'll see phases scroll by:

```
● nw-solution-architect(Fill roadmap skeleton)    ← Planning (~30s)
● nw-software-crafter(Execute step 01-01)         ← Writing code (~2-3 min)
● nw-software-crafter-reviewer(Adversarial review) ← Quality check (~1 min)
```

The agent reads your four tests, plans an implementation, and builds code that makes each test pass — one at a time, following the TDD cycle.

### Messages you can safely ignore

Lines like these are normal internal coordination, not errors:

- `PreToolUse:Task hook error` — DES validation checkpoint
- `DES_MARKERS_MISSING` — Internal formatting check, auto-retries

### Verify success

When delivery completes, run:

```bash
pytest tests/ -v
```

Expected:

```
tests/test_markdown.py::test_converts_heading_to_html PASSED
tests/test_markdown.py::test_converts_bold_and_italic_text PASSED
tests/test_markdown.py::test_plain_text_returns_as_paragraph PASSED
tests/test_markdown.py::test_converts_unordered_list PASSED

4 passed
```

All green. Try the converter:

```bash
PYTHONPATH=src python3 -c "
from md_converter import markdown_to_html
print(markdown_to_html('# Hello\n\nThis is **bold** and *italic*.\n\n- One\n- Two'))
"
```

You should see something like:

```html
<h1>Hello</h1>
<p>This is <strong>bold</strong> and <em>italic</em>.</p>
<ul>
<li>One</li>
<li>Two</li>
</ul>
```

Your exact output may differ slightly — what matters is that all four Markdown features are converted.

> **If tests fail after delivery**: Run `/nw-deliver` again — it resumes from where it left off and fixes remaining failures.

> **If you see no output for 2+ minutes**: Check the Claude Code status bar at the bottom. A pulsing indicator means it's still working.

*Next: a recap of the test-writing principles you just used.*

---

## Step 6 of 6: What Just Happened (~1 minute)

You started with an empty project and wrote four acceptance tests. nWave turned them into working code. But the real skill you practiced was **writing tests that guide delivery**.

### The Five Principles You Applied

1. **Test the WHAT, not the HOW** — Your tests said "heading becomes `<h1>`", never "use regex to parse". The agent chose its own implementation.

2. **Descriptive names are specifications** — `test_converts_heading_to_html` reads like a requirement. Anyone (human or AI) can understand what "done" means.

3. **Start simple, add complexity** — Heading first, then inline formatting, then lists. Each test built on the previous concept. This is the density ramp.

4. **Edge cases define boundaries** — `test_plain_text_returns_as_paragraph` asks "what happens with no Markdown?" That boundary prevents bugs.

5. **Keep tests independent** — Each test runs alone. No test depends on another test's state. This lets nWave tackle them one at a time.

### What You Built

- A **complete project** from scratch (no starter repo)
- **4 acceptance tests** that serve as a living specification
- A **working Markdown-to-HTML converter** you never had to implement
- **Atomic git commits** tracing every TDD step

### What You Didn't Have to Do

- Write the implementation
- Figure out how to parse Markdown syntax
- Decide on architecture (functions, classes, modules)
- Write additional unit tests (nWave wrote them from your acceptance tests)
- Review the code (the reviewer agent did it)

---

## Next Steps

- **[Tutorial 3: Understanding the Delivery Pipeline](../tutorial-delivery-pipeline/)** — See exactly what happens inside `/nw-deliver` and learn to read the output like a pro
- **[Tutorial 7: Generating Acceptance Tests](../tutorial-distill/)** — Don't want to write tests by hand? `/nw-distill` generates them from user stories
- **Try it on your own project** — Pick a small feature, write 3-4 tests that define "done", and run `/nw-deliver`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ImportError` when running tests before delivery | Expected — the function doesn't exist yet. That's the point of red tests. |
| `ModuleNotFoundError` after delivery | Make sure your venv is active and `pyproject.toml` has `pythonpath = ["src"]` |
| Tests still failing after delivery | Run `/nw-deliver` again — it resumes and fixes remaining failures |
| Agent creates files in wrong location | Check that `src/md_converter/__init__.py` exists before delivery |
| Want to start over | `git stash && git checkout main` then recreate the test file |
| Delivery takes more than 10 minutes | Normal for slower machines. Check the Claude Code status bar for activity. |

---

**Last Updated**: 2026-02-17
