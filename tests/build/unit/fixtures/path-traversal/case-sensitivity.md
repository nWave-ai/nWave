# Test: Case Sensitivity (p2-06)

This test validates platform-specific behavior with path case sensitivity.

## Test Scenario

Attempt to include file with different case:

{{ BUILD:INCLUDE NWave/DATA/CORE/radical-candor.md }}

## Expected Results

- On case-insensitive filesystem (Windows): Path matches, file included successfully
- On case-sensitive filesystem (Linux/Mac): Path doesn't exist, "File not found" error
- In both cases: Security validation passes (path stays within project bounds)
- No security errors - only file not found or success
- Exit code: 0 (if found) or 1 (if not found)
