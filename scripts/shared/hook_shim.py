"""Names of the nWave prepare-commit-msg fallback shim.

The attribution installer writes the shim and the hook checker accepts it. Both
read these names from here, so the banner and the chained-original suffix each
have exactly one owner. Stdlib only: the checker runs under a bare python3.
"""

#: Marks a prepare-commit-msg shim as the current per-repository fallback. The
#: retired shim carried only the "nwave_attribution_hook" substring; retirement
#: removes shims without this marker and preserves shims that carry it.
FALLBACK_MARKER: str = "nwave-attribution-fallback"

#: Suffix of the file a shim chains to: `<hook-type>.nwave-original`.
ORIGINAL_SUFFIX: str = ".nwave-original"
