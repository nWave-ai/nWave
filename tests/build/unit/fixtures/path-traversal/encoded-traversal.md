# Test: Encoded Traversal Patterns (p2-06)

This test validates that encoded directory traversal attempts don't bypass security.

## Test Scenario

Attempt URL-encoded traversal pattern:

{{ BUILD:INCLUDE ..%2F..%2F..%2Fetc%2Fpasswd }}

## Expected Results

- Encoded path treated as literal (no decoding in path resolution)
- Path validation fails due to invalid characters or non-existent file
- Error handling proceeds gracefully
- Exit code: 1 (error detected)
- Security not bypassed by encoding
