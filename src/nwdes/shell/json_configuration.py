"""Read declared configuration files and pass bytes to their pure constructor."""

from pathlib import Path
from types import MappingProxyType

from nwdes.contracts import Built, Defect, Refused, checked
from nwdes.destinations import (
    ConfigurationRefused,
    ConfigurationTier,
    parse_tier,
    readable_setting,
)
from nwdes.shell.ports import ConfigurationRead


def read_configuration_tier(project_root, global_config, tier, scope=None):
    if tier == "global":
        path = Path(global_config)
    elif tier == "repository":
        path = Path(project_root) / ".nwave/config.json"
    else:
        directory = "features" if tier == "feature" else "epics"
        path = Path(project_root) / ".nwave" / directory / scope.id / "config.json"
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return Built(ConfigurationTier(tier, str(path)))
    except OSError as error:
        failed = checked(
            None,
            (
                Defect(
                    f"ConfigurationMalformed: {path}",
                    str(error),
                    "Make this configuration file readable.",
                ),
            ),
        )
        return ConfigurationRefused(
            failed.refusal, ConfigurationTier(tier, str(path), unknown=True)
        )
    return parse_tier(tier, str(path), data)


def configuration_failed(tiers):
    return any(
        isinstance(result, ConfigurationRefused) and result.tier.unknown
        for result in tiers
    )


def read_lane_configuration(root, global_config):
    tiers = tuple(
        read_configuration_tier(root, global_config, tier)
        for tier in ("global", "repository")
    )
    defects = tuple(
        defect
        for result in tiers
        if isinstance(result, Refused)
        for defect in result.defects
    )
    unavailable = checked(None, defects)
    absent = object()
    values = {}
    for key in ("lanes.trunk", "lanes.disposable", "adr.directory"):
        value = readable_setting(tiers, key, absent)
        if value is not absent:
            values[key] = unavailable if value is None else value
    return ConfigurationRead(
        MappingProxyType(values), defects, configuration_failed(tiers)
    )
