"""Which changed paths are documents. A commit that changes only documents does not change the code a refactor judged.

A document is a Markdown file (a name ending in .md) or any file under the docs folder. Every other path is code.
"""

from __future__ import annotations

from pathlib import PurePosixPath


DOCUMENT_FOLDER = "docs"
DOCUMENT_SUFFIX = ".md"


def is_document(path: str) -> bool:
    """True for a path that is a document; a path that is only named like one (docs-old.txt) is code."""
    pure = PurePosixPath(path)
    return pure.suffix == DOCUMENT_SUFFIX or (
        bool(pure.parts) and pure.parts[0] == DOCUMENT_FOLDER
    )


def is_document_only(paths: list[str]) -> bool:
    """True when the commit changes files and every one of them is a document."""
    return bool(paths) and all(is_document(path) for path in paths)
