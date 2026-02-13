# Test: Null Byte Injection (p2-06)

This test validates that dependency_resolver handles null byte injection attempts gracefully.

## Test Scenario

Attempt null byte injection in path:

{{ BUILD:INCLUDE nWave/data/core/file.md }}

## Expected Results

- Operation completes without crash
- Error handling catches invalid characters if present
- Exit code: 1 (error) or 0 (success) depending on path validity
- No unhandled exceptions from malformed paths
