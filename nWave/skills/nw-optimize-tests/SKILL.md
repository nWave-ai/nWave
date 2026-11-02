---
name: nw-optimize-tests
description: Consolidates a test scope to the fewest tests that preserve coverage and behavior, deleting duplication, parametrize inflation, language-guarantee tests, AST-shape tests, and stale migration nets. An independent read-only reviewer with veto always validates the result.
user-invocable: true
argument-hint: '[scope] - a path, a feature-id (resolves to tests/<id>/), or omit for the full unit suite.'
---

# NW-OPTIMIZE-TESTS

Act when invoked. Do not wait for approval, do not present a plan table, and do
not produce a report artifact.

Dispatch `nw-test-optimizer` over `{scope}` (methodology: `nw-test-optimization`).

Invariants:

- Run the exact project-declared command vector before and after, in the same
  environment and over the same scope. Compare terminal process timing only.
- Production files in the diff: zero.
- Coverage and observed behavior preserved; any drop is justified in the reply.
- Consolidate by deletion, never by adding a test to cover a removed one.
- Tests must prove observable behavior, never source prose or AST shape.

After the mutation, always dispatch `nw-test-optimizer-reviewer` over the
resulting diff. It reads only, and it holds veto: production drift, coverage or
behavior loss, and any deletion not mapped to a stated pattern are refusals the
optimizer must repair before the work is done. Its verdict is prose in the
reply, not an artifact or a schema.

Out of scope: authoring new tests, production refactoring, test infrastructure.
