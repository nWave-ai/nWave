# Test: Mixed Valid and Invalid Paths (p2-06)

This test validates that processing continues after security error is encountered.

## Test Scenario

Document with both valid and malicious paths:

Section A - Valid:
{{ BUILD:INCLUDE nWave/data/core/radical-candor.md }}

Section B - Invalid:
{{ BUILD:INCLUDE ../../../etc/passwd }}

Section C - Valid:
{{ BUILD:INCLUDE nWave/data/core/radical-candor.md }}

## Expected Results

- Section A: Valid path processed successfully, content included
- Section B: Traversal blocked, error reported, marker unchanged
- Section C: Valid path processed successfully, content included
- Exit code: 1 (due to error in Section B)
- Processing continues after security error
