"""The label names the silence rule and the maintainer reply command share."""

from __future__ import annotations


MARKER = "fixed-awaiting-reply"
CLOSED_LABEL = "closed-after-silence"
KEEP_OPEN = "keep-open"
ALL_LABELS = (MARKER, CLOSED_LABEL, KEEP_OPEN)
