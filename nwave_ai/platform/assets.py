"""Which tree's shipped asset should this command read -- installed, or repo?

An `nwave-ai` command that reads a shipped asset (`nWave/data/...`, `nWave/flavors`,
...) has historically resolved it relative to its OWN module file. Under the
installed shim that is the installed copy, while `--root` defaults to the
operator's current directory -- the repo. So the command validates the repo's
skills against the INSTALLED manifest, and says PASS.

That is not a missing input: the runtime has ALREADY detected the developer
checkout and printed `developer checkout detected via .git adjacency at '<the
worktree>'` on the very same run. It knows where you are and reads elsewhere.

This boundary exists because packaged assets can legitimately be present in
both a developer checkout and an installed distribution. Their contents may
differ, so choosing one tree implicitly would validate a different artifact
from the one the operator named.

The rule this module implements
-------------------------------
Ambiguity, not location, is what must be refused. When a developer checkout is
present AND carries its own copy of the asset AND that copy DIFFERS from the
installed one, the answer is AMBIGUOUS and the caller must degrade LOUD --
never pick one silently. When the two agree, or only one exists, there is
nothing to be ambiguous about and refusing would be ceremony: that is why the
"differs" test is load-bearing and not decoration (`nWave/dispatch` is
byte-identical today and must keep resolving without complaint).

Only dependency: Python. No git binary -- a checkout is recognised by `.git`
adjacency, exactly as the freshness probe recognises it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class AssetOrigin(str, Enum):
    """Which tree the asset was taken from."""

    INSTALLED = "INSTALLED"
    REPO = "REPO"
    #: A developer checkout and the installed tree both carry it, and they
    #: disagree. Never resolved by guessing.
    AMBIGUOUS = "AMBIGUOUS"
    ABSENT = "ABSENT"


@dataclass(frozen=True)
class AssetResolution:
    """The chosen path, the tree it came from, and why."""

    origin: AssetOrigin
    path: Path | None
    installed: Path
    repo: Path | None
    detail: str

    @property
    def is_usable(self) -> bool:
        return self.path is not None and self.origin is not AssetOrigin.AMBIGUOUS


def installed_package_root() -> Path:
    """The directory that CONTAINS the shipped ``nWave/`` tree for this runtime.

    Derived from the ``nwave_ai`` package location rather than a fixed ``parents[N]``
    hop, because call sites sit at different depths (``nwave_ai/cli.py`` counts
    one, ``nwave_ai/hooks/x.py`` counts two) and a hard-coded
    count is one refactor away from silently pointing at the wrong directory.
    """
    import nwave_ai

    package_dir = Path(next(iter(nwave_ai.__path__))).resolve()
    adjacent = package_dir.parent
    enclosing = adjacent.parent

    # ``nwave_ai`` has four supported physical layouts:
    #
    #   checkout:  <root>/nwave_ai           + <root>/nWave
    #   bundled:   <root>/python/nwave_ai    + <root>/nWave
    #   wheel:     <root>/nwave_ai           + <root>/nWave
    #   bundled:   <root>/nWave/lib/python/nwave_ai + <root>/nWave
    #
    # Select the nearest ancestor that actually owns the shipped tree instead
    # of encoding a source-layout parent depth. The bundled wheel layout has
    # two additional ancestors between ``nwave_ai`` and the site-packages root.
    for candidate in package_dir.parents:
        if (candidate / "nWave").is_dir():
            return candidate

    # Preserve the historical source/bundled diagnostic when neither tier is
    # complete, while naming the conventional wheel root accurately.
    if adjacent.name in {"site-packages", "dist-packages"}:
        return adjacent
    return enclosing


def find_developer_checkout(start: Path | None = None) -> Path | None:
    """The nearest ancestor holding a ``.git`` entry, or None.

    ``.git`` is a directory in a normal clone and a file in a linked worktree;
    both count, which is what makes this work inside a swarm worktree.
    """
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _digest(path: Path) -> str | None:
    """Content digest of a file or a whole directory, or None if absent."""
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if path.is_dir():
        accumulator = hashlib.sha256()
        for entry in sorted(path.rglob("*")):
            if entry.is_file():
                accumulator.update(entry.relative_to(path).as_posix().encode())
                accumulator.update(entry.read_bytes())
        return accumulator.hexdigest()
    return None


def resolve_packaged_asset(
    relative: str, *, start: Path | None = None, installed: Path | None = None
) -> AssetResolution:
    """Decide which copy of a shipped asset this invocation should read.

    ``installed`` lets a caller name the exact "installed" candidate directly
    (e.g. a module-level default the caller already resolves and wants tests
    to be able to redirect) instead of deriving the nearest containing ancestor.
    Ancestors lacking the requested asset do not mask a complete outer tier.
    """
    installed_path = installed
    if installed_path is None:
        import nwave_ai

        package_dir = Path(next(iter(nwave_ai.__path__))).resolve()
        installed_path = next(
            (
                candidate / relative
                for candidate in package_dir.parents
                if (candidate / relative).exists()
            ),
            installed_package_root() / relative,
        )
    checkout = find_developer_checkout(start)
    repo = (checkout / relative) if checkout is not None else None

    installed_digest = _digest(installed_path)
    repo_digest = _digest(repo) if repo is not None else None

    if repo_digest is None and installed_digest is None:
        return AssetResolution(
            AssetOrigin.ABSENT,
            None,
            installed_path,
            repo,
            f"`{relative}` exists in neither the installed tree nor the checkout",
        )
    if repo_digest is None:
        return AssetResolution(
            AssetOrigin.INSTALLED,
            installed_path,
            installed_path,
            repo,
            f"read from the installed tree at {installed_path}",
        )
    if installed_digest is None:
        return AssetResolution(
            AssetOrigin.REPO,
            repo,
            installed_path,
            repo,
            f"read from the developer checkout at {repo}",
        )
    if installed_digest == repo_digest:
        # No ambiguity: the two carry the same bytes. Refusing here would be
        # ceremony charged for nothing.
        return AssetResolution(
            AssetOrigin.REPO,
            repo,
            installed_path,
            repo,
            f"installed and checkout copies of `{relative}` are identical",
        )
    return AssetResolution(
        AssetOrigin.AMBIGUOUS,
        None,
        installed_path,
        repo,
        (
            f"`{relative}` differs between the developer checkout "
            f"({repo}) and the installed tree ({installed_path})"
        ),
    )
