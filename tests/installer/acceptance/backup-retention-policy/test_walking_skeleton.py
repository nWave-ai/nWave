"""Walking Skeleton bindings for backup-retention-policy.

Strategy C (Real local). Both walking skeletons exercise real BackupManager
against a real filesystem on tmp_path with HOME and CLAUDE_CONFIG_DIR
isolated via monkeypatch.
"""

from pytest_bdd import scenario


@scenario(
    "walking-skeleton.feature",
    "Eleventh install prunes the oldest backup so disk usage stays bounded",
)
def test_ws_eleventh_install_prunes_oldest():
    """Walking skeleton: full retention round-trip on real filesystem."""


@scenario(
    "walking-skeleton.feature",
    "After retention prunes, restore still finds Marco's most recent backup",
)
def test_ws_restore_after_retention():
    """Walking skeleton: retention preserves restore semantics (D2)."""


@scenario(
    "walking-skeleton.feature",
    "Eleventh install through the installer entry point prunes the oldest backup",
)
def test_ws_outer_seam_wiring_prunes_oldest():
    """Walking skeleton: DWD-10 outer-seam wiring proof.

    Drives ``NWaveInstaller.create_backup()`` — the same seam ``main()``
    invokes — and proves retention runs as part of that wrapper. Inner-seam
    tests above prove the retention algorithm is correct; this test proves
    the wrapper actually wires it in.
    """
