"""Legacy decision-column normalization (issue #50 deprecation window).

The commitment-table decision column and its reference token were renamed from
``DDD`` / ``DDD-N`` to ``DDR`` / ``DDR-N`` ("Design Decision Record") because the
old abbreviation collided with Domain-Driven Design. Validation accepts both
during the deprecation window; this helper proactively rewrites a legacy
feature-delta.md to the canonical ``DDR`` form so projects can drop the alias.

Scope is deliberately conservative — it only rewrites tokens that belong to the
feature-delta commitment-table convention:

  - the ``DDD`` cell in a commitments-table header row → ``DDR``
  - ``DDD-N`` reference tokens (cells, design-decision bullets, impact citations)
    → ``DDR-N``

It does NOT touch arbitrary prose, so an unrelated ``DDD`` word elsewhere in the
document is left alone. The function is idempotent: a document already in DDR
form is returned unchanged.
"""

from __future__ import annotations

import re


# A pipe-delimited table header row whose third column is exactly DDD.
_HEADER_DDD = re.compile(r"(^\|[^|\n]*\|[^|\n]*\|\s*)DDD(\s*\|)", re.MULTILINE)
# A DDD-N reference token (word-boundary, case-sensitive on the prefix).
_REF_DDD_N = re.compile(r"\bDDD-(\d+)")


def normalize_decision_refs(text: str) -> str:
    """Rewrite legacy DDD / DDD-N feature-delta tokens to the DDR form.

    Idempotent: returns ``text`` unchanged when no legacy tokens are present.
    """
    text = _HEADER_DDD.sub(r"\1DDR\2", text)
    text = _REF_DDD_N.sub(r"DDR-\1", text)
    return text
