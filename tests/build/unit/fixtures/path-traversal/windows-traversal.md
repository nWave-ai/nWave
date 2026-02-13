# Test: Windows Path Traversal Patterns (p2-06)

This test validates that dependency_resolver blocks Windows-style directory traversal.

## Test Scenario

Attempt Windows-style traversal with backslashes:

{{ BUILD:INCLUDE nWave\\data\\..\\..\\windows\\system32\\config }}

## Expected Results

- Error reported for traversal attempt
- Windows system directory NOT accessed
- Exit code: 1 (error detected)
- Platform-independent path validation works across forward and backslashes
