"""Scope-parity AST fitness test ported from nwave-software-factory.

Ensures every caller of `commit_verifier.verify_commit(...)` passes a
`feature_id_filter` keyword argument with a non-trivial value. Without this,
a step with `Step-Id: 01-02` in feature A could be wrongly satisfied by a
commit from feature B carrying the same step number.

Defence is structural (AST walk over `src/des/`), not behavioural — it
guarantees the contract at compile-time-equivalent on every commit. SF parity
port of `test_workflow_executor_scope_parity.py` (commit ae109bd8).

Step-Id: 01-01, 01-02
Task-Id: fix-scope-parity-feature-id-filter
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


_SRC_DES = Path(__file__).resolve().parents[4] / "src" / "des"


@dataclass(frozen=True)
class _VerifyCommitCall:
    """A located `*.verify_commit(...)` call site."""

    file: str  # path relative to repo root, e.g. "src/des/application/foo.py"
    line: int
    caller: str  # enclosing function/method name, e.g. "validate"
    keywords: tuple[str, ...]  # kwarg names actually passed at the call site
    feature_id_value_dump: str | None  # ast.dump of the kwarg value if present


def _collect_verify_commit_calls() -> list[_VerifyCommitCall]:
    """AST-walk every `.py` under `src/des/` (exclude `__pycache__`).

    For each `ast.Call` whose `.func` is an attribute access named
    `verify_commit`, record the call site + enclosing function name + keyword
    names + the AST dump of the `feature_id_filter` value when present.
    """
    calls: list[_VerifyCommitCall] = []
    repo_root = _SRC_DES.parent.parent  # nWave-dev/

    for py_file in _SRC_DES.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:  # pragma: no cover -- defensive
            continue

        # Build a line -> enclosing-function-name lookup for the file.
        scopes: list[tuple[int, int, str]] = []  # (start_line, end_line, name)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno)
                scopes.append((node.lineno, end, node.name))

        def _enclosing(line: int, _scopes: list[tuple[int, int, str]] = scopes) -> str:
            best = ("<module>", -1)
            for start, end, name in _scopes:
                if start <= line <= end and start > best[1]:
                    best = (name, start)
            return best[0]

        rel = py_file.relative_to(repo_root).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr != "verify_commit":
                continue
            kw_names = tuple(kw.arg for kw in node.keywords if kw.arg)
            feature_id_value_dump: str | None = None
            for kw in node.keywords:
                if kw.arg == "feature_id_filter":
                    feature_id_value_dump = ast.dump(kw.value)
                    break
            calls.append(
                _VerifyCommitCall(
                    file=rel,
                    line=node.lineno,
                    caller=_enclosing(node.lineno),
                    keywords=kw_names,
                    feature_id_value_dump=feature_id_value_dump,
                )
            )
    return calls


def test_every_commit_verifier_caller_passes_feature_id_filter() -> None:
    """Every `verify_commit(...)` call site MUST pass `feature_id_filter=...`.

    Prevents the SF-identified failure mode: cross-feature commit confusion
    where a step in feature A is satisfied by a commit from feature B carrying
    the same step number. The defence is AND-semantics on the git grep
    (Step-Id matches AND Task-Id matches), driven from this kwarg.
    """
    calls = _collect_verify_commit_calls()
    assert calls, (
        "AST walk found ZERO verify_commit call sites under src/des/. "
        "Either the AST walk is broken or all callers were deleted -- both "
        "are bugs."
    )
    violations = [c for c in calls if "feature_id_filter" not in c.keywords]
    assert not violations, (
        "verify_commit callers MUST pass feature_id_filter kwarg (SF parity, "
        "prevents cross-feature commit confusion). Offending call sites:\n"
        + "\n".join(f"  - {v.file}:{v.line} in {v.caller}()" for v in violations)
    )


_TRIVIAL_DUMPS: frozenset[str] = frozenset(
    {
        "Constant(value=None)",
        "Constant(value='')",
        "Constant(value='None')",
        "Constant(value=False)",
        "Constant(value=0)",
    }
)


def test_feature_id_filter_kwarg_is_non_trivial() -> None:
    """`feature_id_filter` value MUST NOT be a trivial literal.

    Accepts: attribute access (`context.project_id`), names (`feature_id`) --
    anything that resolves at runtime to a real feature identifier.

    Rejects literal `None`, empty string, the string `"None"`, `False`, `0`.
    """
    calls = _collect_verify_commit_calls()
    callers_with_kwarg = [c for c in calls if "feature_id_filter" in c.keywords]
    assert callers_with_kwarg, (
        "No verify_commit caller passes feature_id_filter -- the prior test "
        "(test_every_commit_verifier_caller_passes_feature_id_filter) is the "
        "primary failure indicator. This test is vacuously trivial without "
        "callers; treat it as a confirmation that values are meaningful."
    )
    trivial = [
        c for c in callers_with_kwarg if c.feature_id_value_dump in _TRIVIAL_DUMPS
    ]
    assert not trivial, (
        "feature_id_filter kwarg MUST resolve to a real feature id -- "
        "trivial literals defeat the cross-feature defence. Offending sites:\n"
        + "\n".join(
            f"  - {v.file}:{v.line} in {v.caller}() -> value dump: "
            f"{v.feature_id_value_dump}"
            for v in trivial
        )
    )


def _is_or_none_clamp(value_dump: str | None) -> bool:
    """Return True if the kwarg value is an `<expr> or None` BoolOp clamp.

    Matches `ast.dump` output for `<anything> or None` literally -- the
    `BoolOp(op=Or(), values=[..., Constant(value=None)])` shape. Callers
    that wrap a feature id with `or None` silently fall back to a no-filter
    git grep when the left operand is falsy (e.g. empty string), defeating
    the AND-semantics defence at runtime.
    """
    if value_dump is None:
        return False
    return value_dump.startswith("BoolOp(op=Or()") and value_dump.endswith(
        "Constant(value=None)])"
    )


def test_feature_id_filter_kwarg_is_not_or_none_clamp() -> None:
    """`feature_id_filter` MUST NOT use the `<expr> or None` defensive clamp.

    The clamp pattern `context.project_id or None` collapses to `None` when
    the left operand is empty-string/0/False, silently defeating the
    AND-semantics defence at the verifier port. The contract is: callers
    must validate non-emptiness upstream and pass the value directly.

    This test catches D2 (reviewer finding on commit e1253c867) at the
    structural layer -- if any caller re-introduces the clamp, this fails.
    """
    calls = _collect_verify_commit_calls()
    callers_with_kwarg = [c for c in calls if "feature_id_filter" in c.keywords]
    assert callers_with_kwarg, (
        "No verify_commit caller passes feature_id_filter -- prior tests "
        "are the primary failure indicators. This test is vacuously trivial "
        "without callers."
    )
    clamps = [
        c for c in callers_with_kwarg if _is_or_none_clamp(c.feature_id_value_dump)
    ]
    assert not clamps, (
        "feature_id_filter kwarg MUST NOT use `<expr> or None` defensive "
        "clamp -- the clamp silently defeats AND-semantics when the left "
        "operand is falsy. Validate non-emptiness upstream instead. "
        "Offending sites:\n"
        + "\n".join(
            f"  - {v.file}:{v.line} in {v.caller}() -> value dump: "
            f"{v.feature_id_value_dump}"
            for v in clamps
        )
    )
