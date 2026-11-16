"""The four feature documents of a run, rendered from its journal by the briefer.

brief.md is the summary followed by the decisions taken; architecture.md is the design step and acceptance.md the
oracle step, each as its current record; TRACE.md is the trace of recorded paths, kept under its own name because
no nwdes document has its content. Only the step names of the shipped schema are named here.
"""

from __future__ import annotations

from nwexpress.application.briefer import Briefer
from nwexpress.domain.feature_directory import (
    ACCEPTANCE_NAME,
    ARCHITECTURE_NAME,
    BRIEF_NAME,
    TRACE_NAME,
)
from nwexpress.domain.journal import Journal


ARCHITECTURE_STEP = "design"
ACCEPTANCE_STEP = "oracle"


def feature_document_texts(
    briefer: Briefer, journal: Journal
) -> tuple[tuple[str, str], ...]:
    """(file name, Markdown text) pairs, in the order the documents are written."""
    return (
        (
            BRIEF_NAME,
            briefer.render("summary", journal)
            + "\n"
            + briefer.render("decisions", journal),
        ),
        (ARCHITECTURE_NAME, briefer.step_document(ARCHITECTURE_STEP, journal)),
        (ACCEPTANCE_NAME, briefer.step_document(ACCEPTANCE_STEP, journal)),
        (TRACE_NAME, briefer.render("trace", journal)),
    )
