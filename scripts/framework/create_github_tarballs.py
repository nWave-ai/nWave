#!/usr/bin/env python3
"""
nWave GitHub Tarball Creator

Creates distributable tarballs for GitHub Releases from the nWave/ source or dist/ directory.
These tarballs are uploaded to GitHub Releases for manual installation.
(The PyPI/pipx distribution is handled separately by hatchling.)

Usage:
    python create_github_tarballs.py [--output-dir DIR] [--version VERSION]

Requirements:
    - nWave/ source directory with agents/ and commands/nw/ (or tasks/nw/)
    - Python 3.7+

Output:
    - dist/releases/nwave-claude-code-{version}.tar.gz
    - dist/releases/nwave-codex-{version}.tar.gz
    - dist/releases/install-nwave-claude-code.py
    - dist/releases/install-nwave-codex.py
"""

import argparse
import json
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path


__version__ = "1.0.0"


class GitHubTarballCreator:
    """Creates distributable tarballs for GitHub Releases."""

    def __init__(
        self,
        version: str | None = None,
        output_dir: Path | None = None,
        source_dir: Path | None = None,
    ):
        """Initialize packager."""
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.dist_dir = self.project_root / "dist"
        self.source_dir = source_dir or (self.project_root / "nWave")
        self.using_dist = source_dir is not None
        self.version = version or self._get_version()
        self.output_dir = output_dir or (self.dist_dir / "releases")

    def _get_version(self) -> str:
        """Get version from framework-catalog.yaml."""
        catalog_file = self.project_root / "nWave" / "framework-catalog.yaml"

        if not catalog_file.exists():
            return "dev"

        try:
            import re

            content = catalog_file.read_text(encoding="utf-8")
            match = re.search(r'^version:\s*["\']?([0-9.]+)', content, re.MULTILINE)
            if match:
                return match.group(1)
        except Exception:
            pass

        return "dev"

    def _log(self, message: str, level: str = "INFO"):
        """Print log message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def validate_source(self) -> bool:
        """Validate that nWave/ source directory exists with agents and commands."""
        if not self.source_dir.exists():
            self._log(
                f"nWave source directory not found at: {self.source_dir}", "ERROR"
            )
            return False

        agents_dir = self.source_dir / "agents"
        # Support both dist/ layout (commands/nw) and nWave/ source layout (tasks/nw)
        commands_dir = self.source_dir / "commands" / "nw"
        if not commands_dir.exists():
            commands_dir = self.source_dir / "tasks" / "nw"

        if not agents_dir.exists() or not commands_dir.exists():
            self._log("Required directories not found in source", "ERROR")
            return False

        agent_count = len(list(agents_dir.rglob("*.md")))
        command_count = len(list(commands_dir.rglob("*.md")))

        if agent_count == 0 or command_count == 0:
            self._log("No agents or commands found in source", "ERROR")
            return False

        self._log(f"Found {agent_count} agents and {command_count} commands")
        return True

    def create_package_structure(self, package_name: str) -> Path:
        """Create temporary package directory structure."""
        temp_dir = self.output_dir / "tmp" / package_name
        temp_dir.mkdir(parents=True, exist_ok=True)

        if self.using_dist:
            # dist/ layout: already in install-target format
            # agents/nw/, commands/nw/, templates/, skills/nw/, lib/python/des/
            for subdir in [
                "agents",
                "commands",
                "templates",
                "skills",
                "scripts",
                "lib",
            ]:
                src = self.source_dir / subdir
                if src.exists():
                    dst = temp_dir / subdir
                    shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            # nWave/ source layout: needs mapping
            # Copy agents from nWave/agents/
            agents_src = self.source_dir / "agents"
            agents_dst = temp_dir / "agents" / "nw"
            agents_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                agents_src,
                agents_dst,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("legacy"),
            )

            # Copy commands from nWave/tasks/nw/
            commands_src = self.source_dir / "tasks" / "nw"
            commands_dst = temp_dir / "commands" / "nw"
            commands_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(commands_src, commands_dst, dirs_exist_ok=True)

            # Copy scripts if they exist
            scripts_src = self.source_dir / "scripts"
            if scripts_src.exists():
                scripts_dst = temp_dir / "scripts"
                scripts_dst.mkdir(parents=True, exist_ok=True)
                for script_file in scripts_src.glob("*.py"):
                    shutil.copy2(script_file, scripts_dst / script_file.name)

            # Copy templates
            templates_src = self.source_dir / "templates"
            if templates_src.exists():
                templates_dst = temp_dir / "templates"
                templates_dst.mkdir(parents=True, exist_ok=True)
                # Copy canonical schema
                schema_file = templates_src / "step-tdd-cycle-schema.json"
                if schema_file.exists():
                    shutil.copy2(schema_file, templates_dst / schema_file.name)

        # Create package manifest
        self._create_package_manifest(temp_dir, package_name)

        return temp_dir

    def _create_package_manifest(self, package_dir: Path, package_name: str):
        """Create manifest file for package."""
        agents_dir = package_dir / "agents" / "nw"
        commands_dir = package_dir / "commands" / "nw"

        manifest = {
            "package_name": package_name,
            "framework": "nWave",
            "version": self.version,
            "packaged_at": datetime.now().isoformat(),
            "packager_version": __version__,
            "contents": {
                "agents": len(list(agents_dir.glob("*.md")))
                if agents_dir.exists()
                else 0,
                "commands": len(list(commands_dir.glob("*.md")))
                if commands_dir.exists()
                else 0,
                "scripts": len(list((package_dir / "scripts").glob("*.py")))
                if (package_dir / "scripts").exists()
                else 0,
                "templates": len(list((package_dir / "templates").glob("*.json")))
                if (package_dir / "templates").exists()
                else 0,
            },
            "installation": {
                "target": "~/.claude/",
                "installer": f"install-{package_name}.py",
            },
        }

        manifest_file = package_dir / "MANIFEST.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # Also create README
        readme_content = f"""# nWave Framework Package

**Version:** {self.version}
**Package:** {package_name}
**Packaged:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Contents

- **Agents:** {manifest["contents"]["agents"]} specialized agents
- **Commands:** {manifest["contents"]["commands"]} workflow commands
- **Scripts:** {manifest["contents"]["scripts"]} utility scripts
- **Templates:** {manifest["contents"]["templates"]} schema templates

## Installation

Use the standalone installer:

```bash
python install-{package_name}.py
```

Or manually extract and copy to `~/.claude/`:

```bash
tar -xzf {package_name}-{self.version}.tar.gz
cp -r {package_name}/agents ~/.claude/
cp -r {package_name}/commands ~/.claude/
```

## Documentation

Visit: https://github.com/nWave-ai/nWave

## License

MIT License - See repository for details
"""

        readme_file = package_dir / "README.md"
        readme_file.write_text(readme_content, encoding="utf-8")

    def create_tarball(self, package_dir: Path, package_name: str) -> Path:
        """Create compressed tarball from package directory."""
        tarball_name = f"{package_name}-{self.version}.tar.gz"
        tarball_path = self.output_dir / tarball_name

        self._log(f"Creating tarball: {tarball_name}")

        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(package_dir, arcname=package_name)

        size_mb = tarball_path.stat().st_size / (1024 * 1024)
        self._log(f"Created tarball: {tarball_path} ({size_mb:.2f} MB)")

        return tarball_path

    def copy_installer(self, installer_name: str):
        """Copy installer script to releases directory."""
        installer_src = self.dist_dir / installer_name
        installer_dst = self.output_dir / installer_name

        if installer_src.exists():
            shutil.copy2(installer_src, installer_dst)
            installer_dst.chmod(0o755)  # Make executable
            self._log(f"Copied installer: {installer_name}")
        else:
            self._log(f"Installer not found: {installer_src}", "WARNING")

    def create_claude_code_package(self) -> bool:
        """Create Claude Code IDE package."""
        self._log("\n=== Creating Claude Code Package ===")

        package_name = "nwave-claude-code"

        # Create package structure
        package_dir = self.create_package_structure(package_name)

        # Create tarball
        self.create_tarball(package_dir, package_name)

        # Copy installer
        self.copy_installer("install-nwave-claude-code.py")

        # Cleanup temp directory
        shutil.rmtree(package_dir.parent)

        return True

    def create_codex_package(self) -> bool:
        """Create Codex package (alternative IDE format)."""
        self._log("\n=== Creating Codex Package ===")

        package_name = "nwave-codex"

        # Create package structure (same as Claude Code for now)
        package_dir = self.create_package_structure(package_name)

        # Create tarball
        self.create_tarball(package_dir, package_name)

        # Copy installer (will create Codex installer separately)
        # For now, use same structure as Claude Code
        self._log("Codex package uses same structure as Claude Code")

        # Cleanup temp directory
        shutil.rmtree(package_dir.parent)

        return True

    def create_release_notes(self):
        """Create release notes file."""
        release_notes = f"""# nWave Framework Release {self.version}

**Release Date:** {datetime.now().strftime("%Y-%m-%d")}

## Packages

This release includes the following packages:

### Claude Code IDE
- **Package:** `nwave-claude-code-{self.version}.tar.gz`
- **Installer:** `install-nwave-claude-code.py`
- **Installation:**
  ```bash
  python install-nwave-claude-code.py
  ```

### Codex Format
- **Package:** `nwave-codex-{self.version}.tar.gz`
- **Installation:** Extract to `~/.claude/` directory

## Installation Instructions

### Quick Install (Recommended)

Download and run the installer:

```bash
curl -O https://github.com/nWave-ai/nWave/releases/download/v{self.version}/install-nwave-claude-code.py
python install-nwave-claude-code.py
```

### Manual Install

1. Download the package: `nwave-claude-code-{self.version}.tar.gz`
2. Extract: `tar -xzf nwave-claude-code-{self.version}.tar.gz`
3. Copy to Claude config:
   ```bash
   cp -r nwave-claude-code/agents ~/.claude/
   cp -r nwave-claude-code/commands ~/.claude/
   ```

## What's Included

- 24 specialized agents for the nWave methodology
- 21 workflow commands for DISCUSS→DESIGN→DISTILL→DEVELOP→DELIVER
- Utility scripts for target project integration
- Schema templates for step file validation

## Documentation

- **Repository:** https://github.com/nWave-ai/nWave
- **Installation Guide:** docs/installation/INSTALL.md
- **Troubleshooting:** docs/troubleshooting/TROUBLESHOOTING.md

## Support

- Issues: https://github.com/nWave-ai/nWave/issues
- Discussions: https://github.com/nWave-ai/nWave/discussions

---
Generated by nWave GitHub Tarball Creator v{__version__}
"""

        release_notes_file = self.output_dir / f"RELEASE_NOTES_{self.version}.md"
        release_notes_file.write_text(release_notes, encoding="utf-8")
        self._log(f"Created release notes: {release_notes_file}")

    def run(self) -> bool:
        """Main packaging workflow."""
        self._log("=" * 60)
        self._log(f"nWave GitHub Tarball Creator v{__version__}")
        self._log(f"Creating release packages for version: {self.version}")
        self._log("=" * 60)

        # Validate source
        if not self.validate_source():
            return False

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._log(f"Output directory: {self.output_dir}")

        # Create packages
        if not self.create_claude_code_package():
            return False

        if not self.create_codex_package():
            return False

        # Create release notes
        self.create_release_notes()

        # Summary
        self._log("\n" + "=" * 60)
        self._log("Release packages created successfully!")
        self._log("=" * 60)
        self._log(f"\nPackages created in: {self.output_dir}")
        self._log("\nFiles created:")
        for file in sorted(self.output_dir.glob("*")):
            if file.is_file():
                size_mb = file.stat().st_size / (1024 * 1024)
                self._log(f"  - {file.name} ({size_mb:.2f} MB)")

        self._log("\nNext steps:")
        self._log("1. Test the installers locally")
        self._log("2. Create a new GitHub release")
        self._log("3. Upload the packages and installers")
        self._log("4. Update release notes with changelog")

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create nWave GitHub Release tarballs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        help="Version string for the release (default: read from framework-catalog.yaml)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for packages (default: dist/releases/)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Source directory (default: nWave/). Use dist/ for pre-built layout.",
    )

    args = parser.parse_args()

    creator = GitHubTarballCreator(
        version=args.version, output_dir=args.output_dir, source_dir=args.source_dir
    )

    success = creator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
