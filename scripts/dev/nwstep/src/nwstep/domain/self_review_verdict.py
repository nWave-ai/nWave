"""One self-review answer: 'pass - evidence', 'fixed:evidence' or 'n/a:reason'; fail and debt are refused."""

from __future__ import annotations


class SelfReviewVerdict:
    PASS = "pass"
    FIXED = "fixed"
    NOT_APPLICABLE = "n/a"
    REFUSED = ("fail", "debt")

    def __init__(self, word: str, evidence: str) -> None:
        self.word = word
        self.evidence = evidence

    @classmethod
    def parse(cls, item: str) -> SelfReviewVerdict:
        """Read the answer after 'D1:'. Raises ValueError with the reason it is not accepted."""
        body = item.partition(":")[2].strip()
        if body.startswith("fixed:"):
            return cls(cls.FIXED, body[len("fixed:") :].strip())
        if body.startswith("n/a:"):
            return cls(cls.NOT_APPLICABLE, body[len("n/a:") :].strip())
        word, _, evidence = body.partition(" - ")
        if word.strip() == cls.PASS:
            return cls(cls.PASS, evidence.strip())
        if word.strip() in cls.REFUSED:
            raise ValueError(
                f"'{word.strip()}' is not accepted: fix it now, then record 'fixed:' with the evidence, or justify n/a"
            )
        raise ValueError(
            "the verdict is 'pass - evidence', 'fixed:evidence' or 'n/a:reason'"
        )
