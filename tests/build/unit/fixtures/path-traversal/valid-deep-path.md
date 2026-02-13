# Test: Valid Deep Path (p2-06)

This test validates that dependency_resolver allows valid deeply nested files within project.

## Test Scenario

Include valid file deep within project structure:

{{ BUILD:INCLUDE nWave/data/core/radical-candor.md }}

## Expected Results

- File content successfully included
- No security error reported
- Exit code: 0 (success)
- Content visible in output, proving valid paths still work
