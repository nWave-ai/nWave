"""Pure law for FEATURE-scoped document destinations.

Project scope keeps the flat ``documents.<wave>.destination`` keys.  Feature
scope resolves every wave independently through
``default -> global documents.feature -> project documents.feature ->
feature file documents`` and never reads the flat project keys.
"""

from __future__ import annotations

import re


WAVES = ("discuss", "design", "distill", "devops")
FEATURE_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
PLACEHOLDER = "{feature}"
DEFAULT_TEMPLATES = {
    "discuss": "docs/feature/{feature}/brief.md",
    "design": "docs/feature/{feature}/architecture/brief.md",
    "distill": "docs/feature/{feature}/acceptance/brief.md",
    "devops": "docs/feature/{feature}/operations/brief.md",
}
PROJECT_DEFAULTS = {
    "discuss": "docs/product/brief.md",
    "design": "docs/product/architecture/brief.md",
    "distill": "docs/product/acceptance/brief.md",
    "devops": "docs/product/operations/brief.md",
}


class FeatureDocumentsInvalid(Exception):
    def __init__(self, what: str, why: str, how: str) -> None:
        super().__init__(f"{what}: {why}")
        self.what, self.why, self.how = what, why, how

    def __str__(self) -> str:
        return f"{self.what}: {self.why}"


def valid_feature_id(value: object) -> bool:
    return isinstance(value, str) and FEATURE_ID.fullmatch(value) is not None


def require_feature_id(value: object) -> str:
    if not valid_feature_id(value):
        raise FeatureDocumentsInvalid(
            "InvalidFeatureId",
            f"feature id {value!r} does not match [a-z0-9][a-z0-9-]*",
            "use a lowercase kebab-case feature id such as coherent-delivery-revision",
        )
    return value  # type: ignore[return-value]


def safe_relative_path(value: object, source: str) -> str:
    """A normal repository-local relative file path, nothing more."""
    ok = (
        isinstance(value, str)
        and value.strip() == value
        and value
        and "\\" not in value
        and "\0" not in value
        and not value.startswith("/")
        and not value.endswith("/")
        and all(part not in ("", ".", "..") for part in value.split("/"))
    )
    if not ok:
        raise FeatureDocumentsInvalid(
            "InvalidDocumentDestination",
            f"{source} is not a safe repository-relative file path: {value!r}",
            "use a relative path such as docs/feature/<id>/brief.md without '..'",
        )
    return value  # type: ignore[return-value]


def _destination(tier: object, wave: str) -> object:
    entry = tier.get(wave) if isinstance(tier, dict) else None
    return entry.get("destination") if isinstance(entry, dict) else None


def merge_feature_destinations(
    feature_id: str,
    *,
    global_documents: object = None,
    project_documents: object = None,
    feature_documents: object = None,
) -> dict[str, str]:
    """Resolve one destination per wave for ``feature_id`` or raise."""
    require_feature_id(feature_id)
    templates = dict(DEFAULT_TEMPLATES)
    for label, tier in (("global", global_documents), ("project", project_documents)):
        block = tier.get("feature") if isinstance(tier, dict) else None
        for wave in WAVES:
            value = _destination(block, wave)
            if value is None:
                continue
            if not isinstance(value, str) or PLACEHOLDER not in value:
                raise FeatureDocumentsInvalid(
                    "InvalidFeatureTemplate",
                    f"{label} documents.feature.{wave}.destination must contain "
                    f"{PLACEHOLDER} so that feature ids partition the paths",
                    f"include {PLACEHOLDER} in the template",
                )
            templates[wave] = value
    resolved = {
        wave: safe_relative_path(
            template.replace(PLACEHOLDER, feature_id), f"{wave} feature template"
        )
        for wave, template in templates.items()
    }
    feature_dir = resolved["discuss"].rsplit("/", 1)[0] + "/"
    if isinstance(feature_documents, dict):
        for wave, entry in feature_documents.items():
            if (
                wave not in WAVES
                or not isinstance(entry, dict)
                or set(entry) != {"destination"}
            ):
                raise FeatureDocumentsInvalid(
                    "InvalidFeatureConfig",
                    f"feature documents may only set destination for {WAVES}",
                    "remove the unsupported key",
                )
            path = safe_relative_path(
                entry["destination"], f"feature {feature_id} {wave} destination"
            )
            if not path.startswith(feature_dir):
                raise FeatureDocumentsInvalid(
                    "FeatureDestinationOutsideFeature",
                    f"{path} is outside this feature's directory {feature_dir}",
                    f"place the document under {feature_dir}",
                )
            resolved[wave] = path
    if len(set(resolved.values())) != len(resolved):
        raise FeatureDocumentsInvalid(
            "FeatureDestinationsOverlap",
            "two waves of this feature resolve to the same file",
            "give each wave a distinct destination",
        )
    project_paths = set(PROJECT_DEFAULTS.values())
    for tier in (global_documents, project_documents):
        for wave in WAVES:
            value = _destination(tier, wave)
            if isinstance(value, str):
                project_paths.add(value)
    overlap = project_paths & set(resolved.values())
    if overlap:
        raise FeatureDocumentsInvalid(
            "FeatureDestinationOverlapsProject",
            f"feature destination {sorted(overlap)[0]} is a project document",
            "choose a destination under the feature directory",
        )
    return resolved
