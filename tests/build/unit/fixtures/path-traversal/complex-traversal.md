# Test: Complex Traversal Pattern (p2-06)

This test validates that dependency_resolver blocks complex directory traversal with mixed segments.

## Test Scenario

Attempt to escape using mixed valid and traversal segments:

{{ BUILD:INCLUDE nWave/data/core/../../../../../../etc/passwd }}

## Expected Results

- Error reported: "Path traversal attempt blocked: nWave/data/core/../../../../../../etc/passwd"
- /etc/passwd content NOT included
- Exit code: 1 (error detected)
- No crash or unhandled exception
