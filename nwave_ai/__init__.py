"""nwave-ai: CLI installer for the nWave methodology framework."""

from pathlib import Path


def __getattr__(name: str) -> str:
    """Lazily resolve ``__version__`` via the strict shared producer (PEP 562).

    Ordinary package import performs no resolution; only a direct
    ``nwave_ai.__version__`` access reaches ``scripts.shared.version`` and
    may raise ``VersionResolutionError``. Any other unknown attribute is a
    normal ``AttributeError``.
    """
    if name == "__version__":
        from scripts.shared.version import resolve_product_version

        project_root = Path(__file__).resolve().parent.parent
        return resolve_product_version(project_root).version
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
