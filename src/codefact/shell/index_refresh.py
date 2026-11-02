"""Distribution binding for refresh without a code index."""

from codefact.model import RefreshRefused


def refresh(root) -> RefreshRefused:
    return RefreshRefused(
        reason=(
            "this distribution binds no code index, so there is nothing to "
            "regenerate; queries answer from live sources"
        )
    )
