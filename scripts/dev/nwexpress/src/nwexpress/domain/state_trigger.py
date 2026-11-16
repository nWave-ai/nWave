"""The trigger words of a state, protocol, concurrency or crash window, found in the lines a change adds.

A reason that the change has no state must name each trigger word the added lines use, and say what the change does
not do with it. The vocabulary is words of the mechanisms themselves, not library names of one language, so a file
of any language is read the same way. A word found here is a claim to explain, never a verdict that the change is
unsafe; a word that a comment mentions is named all the same, which is the cost of a lexical check.
"""

from __future__ import annotations

import re

TRIGGER_WORDS: tuple[str, ...] = (
    "append",
    "atomic",
    "concurrent",
    "crash",
    "database",
    "fork",
    "fsync",
    "flush",
    "kill",
    "lock",
    "mutex",
    "process",
    "rename",
    "replace",
    "retry",
    "signal",
    "socket",
    "spawn",
    "sqlite",
    "subprocess",
    "thread",
    "transaction",
    "write",
    "write_text",
)


class StateTrigger:
    @staticmethod
    def in_text(text: str) -> frozenset[str]:
        """The trigger words that occur in the text as whole words."""
        return frozenset(
            word
            for word in TRIGGER_WORDS
            if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text) is not None
        )

    @staticmethod
    def named_by(reason: str, word: str) -> bool:
        return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", reason.lower()) is not None
