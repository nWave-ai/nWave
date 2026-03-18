---
name: nw-copy-paste-quality
description: Copy-paste quality standards — self-contained snippet validation, environment assumptions, expected output contracts, and test script generation
disable-model-invocation: true
---

# Copy-Paste Quality Standards

Every code snippet in a tutorial must execute without modification on the reader's machine. This is the single most important quality attribute -- a broken snippet breaks trust and causes abandonment.

## The Copy-Paste Contract

1. Every code block marked with a language annotation is executable
2. Non-executable blocks (output, pseudo-code, partial examples) use plain text or explicit labels
3. Commands include the full invocation (no implicit working directory changes between blocks)
4. File paths are explicit ("add this to `src/config.py`", not "add this to your config")

## Snippet Categories

### Executable Command
```bash
pytest tests/ -v
```
Reader copies this into their terminal. It must work.

### Expected Output (not executable)
Label these clearly:
```
You should see:
```
```
PASSED test_example.py::test_basic  [100%]
1 passed in 0.02s
```

### File Content (reader creates/edits a file)
Always specify the exact file path:
```markdown
Create `src/handlers/auth.py`:

\`\`\`python
# src/handlers/auth.py
from typing import Optional
...
\`\`\`
```

### Partial Update (reader modifies existing file)
Show context lines for location, mark the new content:
```markdown
In `src/app.py`, add the auth handler after the existing routes:

\`\`\`python
# ... existing routes above ...

# Add this:
from handlers.auth import auth_router
app.include_router(auth_router)
\`\`\`
```

## Environment Assumptions

State these at the top of every tutorial:

- Operating system(s) supported
- Language/runtime version (exact: "Python 3.10+", not "Python")
- Package manager (pip, npm, cargo)
- Shell (bash assumed unless stated otherwise)
- Any required system tools (git, curl, docker)

## Placeholder Policy

Avoid placeholders entirely when possible. When unavoidable:

| Instead of | Use |
|-----------|-----|
| `YOUR_API_KEY_HERE` | A working test/demo key, or instruct the reader to get one first |
| `your-username` | `$(whoami)` or a fixed example value with a note |
| `path/to/project` | The actual path from the starter repo |
| `<version>` | The actual current version number |

If a placeholder is truly required, use a consistent format and explain how to get the real value:
```markdown
Replace `YOUR_TOKEN` with your API token. Get one at: https://example.com/tokens

\`\`\`bash
export API_TOKEN="YOUR_TOKEN"
\`\`\`
```

## Expected Output Guidelines

After every executable command, show expected output:

- For deterministic commands: show exact output
- For commands with variable output (timestamps, IDs): show the shape with variable parts noted
  ```
  You should see something like:
  ```
  ```
  Created project abc-{random-id}
  Server running on http://localhost:{port}
  ```
  The ID and port will differ. What matters: "Created project" and "Server running."
- For AI-generated output: define success by outcome, not exact text (see `ai-workflow-tutorials` skill)

## Test Script Generation

For every tutorial, generate a `test-tutorial.sh` script that validates all copy-paste snippets:

```bash
#!/bin/bash
set -euo pipefail

PASS=0
FAIL=0

check() {
    local step="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "PASS: $step"
        ((PASS++))
    else
        echo "FAIL: $step"
        ((FAIL++))
    fi
}

# Setup
{setup commands from tutorial}

# Step 1
check "Step 1 - {description}" {command from step 1}

# Step 2
check "Step 2 - {description}" {command from step 2}

# Cleanup
{cleanup commands}

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
```

The test script:
- Uses the exact same commands as the tutorial
- Runs in a clean environment (temp directory)
- Cleans up after itself
- Reports pass/fail per step
- Exits non-zero on any failure

## Common Copy-Paste Failures

| Failure | Cause | Prevention |
|---------|-------|------------|
| "Command not found" | Tool not in prerequisites | List all tools in prerequisites |
| "No such file" | Implicit directory change | Use explicit `cd` or absolute paths |
| "Permission denied" | Missing `chmod +x` | Include permission steps |
| "Module not found" | Missing `pip install` | Include install in setup |
| Wrong Python version | System Python vs venv | Specify `python3` and venv activation |
| Shell syntax error | Bash vs zsh differences | Note shell requirements or use POSIX |
