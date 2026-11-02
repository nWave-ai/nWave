"""One read-only view of effective project settings and installed host assets."""

from __future__ import annotations

import os
from pathlib import Path

import nwave_ai
from nwave_ai.doctor.checks.framework_files import FrameworkFilesCheck
from nwave_ai.doctor.context import DoctorContext
from nwave_ai.platform.activation import resolve_activation
from nwave_ai.platform.config import NWaveConfig
from nwave_ai.platform.documentation_density import resolve_density
from nwave_ai.platform.locations import NWaveLocations
from nwave_ai.platform.result import Failure
from scripts.shared.version import VersionResolutionError


def render_status(cwd: Path) -> str:
    """Describe this project's resolved state; never fetch releases or write config."""
    locations = NWaveLocations.resolve(
        home=Path.home(),
        repo_root=cwd,
        agents_home_override=os.environ.get("NWAVE_AGENTS_HOME"),
        claude_config_override=os.environ.get("CLAUDE_CONFIG_DIR"),
        codex_config_override=os.environ.get("CODEX_HOME"),
    )
    if isinstance(locations, Failure):
        raise ValueError(locations.error)
    selected = locations.unwrap()
    config = NWaveConfig(
        cwd=cwd, global_config_path=selected.agents_home / ".nwave" / "config.json"
    )
    effective, sources = config.effective_config_with_sources()
    mode = config.activation_mode
    declared = config.enabled_for_repo
    active = resolve_activation(declared, mode)
    activation = config._global_config_data.get("activation")
    mode_source = (
        "global"
        if isinstance(activation, dict) and activation.get("mode") in ("opt-in", "all")
        else "default"
    )
    activation_source = (
        sources["enabled"] if declared is not None else f"{mode_source} mode"
    )
    try:
        version = nwave_ai.__version__
    except VersionResolutionError:
        version = "unavailable"

    claude_assets = FrameworkFilesCheck().run(DoctorContext.from_defaults()).passed
    codex_dir = selected.codex_config_dir
    codex_markers = (
        selected.agents_home / ".agents" / "skills" / ".nwave-manifest.json",
        codex_dir / "agents" / ".nwave-agents-manifest.json",
        codex_dir / ".nwave-des-manifest.json",
    )
    codex_assets = all(marker.is_file() for marker in codex_markers)

    credit = "on" if effective["attribution"] else "off"
    lines = [
        f"Global activation mode: {mode} ({mode_source})",
        f"This project is {'active' if active else 'inactive'}.",
        f"Activation source: {activation_source}.",
        f"Version: {version} (running CLI; check releases: nwave-ai update --check)",
        f"Attribution: {credit} ({sources['attribution']}); "
        f"nWave co-author credit {'applies to supported commits' if active and effective['attribution'] else 'will not be added here'}.",
        f"Verbosity: {effective['verbosity']} ({sources['verbosity']}).",
        f"Claude Code: {'framework files found' if claude_assets else 'framework files not detected'}.",
        f"Codex: {'installation manifests found' if codex_assets else 'installation manifests not detected'}.",
    ]
    if (
        "update_check" in config._global_config_data
        or "update_check" in config._config_data
    ):
        origins = ", ".join(
            origin
            for origin, data in (
                ("project", config._config_data),
                ("global", config._global_config_data),
            )
            if "update_check" in data
        )
        lines.append(
            f"Retired update_check: ignored ({origins}); no automatic update prompt."
        )
    documentation = config._global_config_data.get("documentation")
    density_config = dict(config._global_config_data)
    if isinstance(documentation, dict):
        density_config["documentation"] = {
            key: value
            for key, value in documentation.items()
            if key != "expansion_prompt"
        }
    try:
        density = resolve_density(density_config)
    except ValueError as error:
        lines.append(f"Documentation density: invalid ({error}); check global config.")
    else:
        reading = (
            "local HTML from the completed wave's DES document"
            if density.mode == "full"
            else "authoritative documents and handoffs"
        )
        lines.append(
            f"Documentation density: {density.mode} ({density.provenance}; "
            f"after an applicable completed wave: {reading})."
        )
    preference = {}
    if isinstance(documentation, dict) and "expansion_prompt" in documentation:
        preference["documentation"] = {
            "expansion_prompt": documentation["expansion_prompt"]
        }
        offer_source = "global"
    else:
        offer_source = "default"
    if "rigor" in config._global_config_data:
        preference["rigor"] = config._global_config_data["rigor"]
        if offer_source == "default":
            offer_source = "global rigor.profile"
    try:
        offer = resolve_density(preference).expansion_prompt
    except ValueError as error:
        lines.append(f"Wave-end explanation: invalid ({error}); check global config.")
    else:
        lines.append(
            f"Wave-end explanation: {offer} ({offer_source}; after completed waves only)."
        )
    if not active:
        lines.append("To activate this project: nwave-ai project enable")
    elif not effective["attribution"]:
        lines.append(
            "To credit future nWave commits: nwave-ai attribution on (machine-wide)."
        )
    lines.append(
        "Host detection is not validation; use nwave-ai doctor for Claude Code or the Codex installer's validation."
    )
    return "\n".join(lines)
