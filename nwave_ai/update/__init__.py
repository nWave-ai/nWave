"""Read-only public-release discovery for the update CLI command."""

from nwave_ai.update.release_discovery import (
    ReleaseDiscoveryRefusal,
    discover_latest_stable_release,
)


__all__ = ["ReleaseDiscoveryRefusal", "discover_latest_stable_release"]
