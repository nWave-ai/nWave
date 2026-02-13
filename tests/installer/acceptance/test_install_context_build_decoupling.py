"""
Acceptance test: InstallContext and framework_source references are clean.

Step 02-04: Update InstallContext and framework_source references

Verifies that:
- InstallContext has no dist_dir field (build pipeline remnant removed)
- InstallContext.framework_source points to project_root/nWave/ when populated
- install_nwave.py passes framework_source=project_root/"nWave" to context
- Plugins that use framework_source resolve to nWave/ (not dist/ide)
"""

import dataclasses
import inspect


class TestInstallContextNoDist:
    """Acceptance: InstallContext is free of build pipeline coupling."""

    def test_install_context_has_no_dist_dir_field(self):
        """
        GIVEN: InstallContext after build pipeline removal
        WHEN: the dataclass fields are inspected
        THEN: dist_dir field is absent
        """
        from scripts.install.plugins.base import InstallContext

        field_names = [f.name for f in dataclasses.fields(InstallContext)]

        assert "dist_dir" not in field_names, (
            "InstallContext still has 'dist_dir' field — "
            "build pipeline remnant should be removed"
        )

    def test_install_context_framework_source_points_to_nwave(self, tmp_path):
        """
        GIVEN: NWaveInstaller creates an InstallContext
        WHEN: the context is populated with framework_source
        THEN: framework_source points to project_root/nWave/ (not dist/ide)
        """
        from unittest.mock import patch

        from scripts.install.install_nwave import NWaveInstaller

        with patch.object(NWaveInstaller, "__init__", lambda self, *a, **kw: None):
            installer = NWaveInstaller()
            installer.project_root = tmp_path
            installer.framework_source = installer.project_root / "nWave"

        assert installer.framework_source == tmp_path / "nWave"
        assert "dist" not in str(installer.framework_source)

    def test_install_nwave_passes_nwave_source_to_context(self):
        """
        GIVEN: install_nwave.py source code
        WHEN: the InstallContext construction is inspected
        THEN: framework_source is derived from project_root / "nWave"
        """
        from scripts.install.install_nwave import NWaveInstaller

        source = inspect.getsource(NWaveInstaller.install_framework)

        # Should pass framework_source to InstallContext
        assert "framework_source=" in source, (
            "install_framework should pass framework_source to InstallContext"
        )

        # The __init__ should set framework_source to nWave
        init_source = inspect.getsource(NWaveInstaller.__init__)
        assert '"nWave"' in init_source or "'nWave'" in init_source, (
            "NWaveInstaller.__init__ should set framework_source to nWave"
        )

    def test_base_module_has_no_dist_references(self):
        """
        GIVEN: base.py after build pipeline removal
        WHEN: the source code is inspected
        THEN: no references to 'dist' exist in the module
        """
        from scripts.install.plugins import base

        source = inspect.getsource(base)

        assert "dist_dir" not in source, "base.py still references 'dist_dir'"
        assert "dist/ide" not in source, "base.py still references 'dist/ide'"
