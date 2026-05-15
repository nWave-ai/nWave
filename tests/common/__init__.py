"""Project-local public test API surfaces (state-delta + future ports).

Test authors should import from submodules of this package — never reach
directly into nWave framework internals. The submodules are thin re-export
wrappers around the canonical implementations and remain stable across
nWave framework refactors.

Submodules:
    state_delta — universe-bound state-transition assertions (Python port,
        canonical for the polyglot matrix).
"""
