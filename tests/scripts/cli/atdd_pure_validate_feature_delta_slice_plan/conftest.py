"""pytest-bdd configuration for the slice-06 acceptance set.

ATDD-pure author-ahead lifecycle: this AT set was authored and reviewed
ahead of its slice's implementation, so its scenarios were RED-by-design
and carried an ``@xfail`` Gherkin tag translated here into a non-strict
``pytest.mark.xfail``.

slice-06 has now been implemented; the slice-06 crafter removed the
``@xfail`` tags from the ``.feature`` file and the translating
``pytest_bdd_apply_tag`` hook from this module at the GREEN phase. The
scenarios are live and pass against the implemented
``validate_feature_delta.py --require-slice-plan`` extension.
"""

from __future__ import annotations
