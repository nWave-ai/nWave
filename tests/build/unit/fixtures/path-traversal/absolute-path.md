# Test: Absolute Path to Sensitive File (p2-06)

This test validates that dependency_resolver blocks absolute paths to files outside project root.

## Test Scenario

Attempt to use absolute path to system file:

{{ BUILD:INCLUDE /etc/passwd }}

## Expected Results

- Error reported: "Path traversal attempt blocked: /etc/passwd"
- /etc/passwd content NOT included
- Exit code: 1 (error detected)
- Processing continues, file reference preserved
