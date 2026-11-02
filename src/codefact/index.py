"""Distribution binding without an indexed provider tier."""

from codefact.model import Coverage, Provider, Snapshot


PROVIDERS: tuple[Provider, ...] = ()


def read_index(snapshot: Snapshot) -> None:
    return None


def coverage(snapshot: Snapshot, recorded, changed=()) -> Coverage:
    return Coverage()


def file_call_edges(snapshot: Snapshot) -> frozenset[tuple[str, str]]:
    return frozenset()
