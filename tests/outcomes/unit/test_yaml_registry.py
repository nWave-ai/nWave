"""Unit/integration test: YamlRegistryAdapter — real filesystem round-trip.

Per nw-tdd-methodology Mandate 6: every adapter has at least one real-I/O
test. This is a filesystem adapter — uses tmp_path and real read/write.
Located under unit/ for tier-mapping convenience; the test exercises the
adapter as integration-style real-IO.
"""

from __future__ import annotations

from pathlib import Path  # used in fixture bodies via tmp_path

import yaml
from nwave_ai.outcomes.adapters.yaml_registry import YamlRegistryAdapter
from nwave_ai.outcomes.domain.outcome import InputShape, Outcome, OutputShape


def test_yaml_registry_round_trip_preserves_schema_version_and_outcomes(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        'schema_version: "0.1"\noutcomes: []\n',
        encoding="utf-8",
    )
    adapter = YamlRegistryAdapter(registry_path)

    outcome = Outcome(
        id="OUT-A",
        kind="specification",
        summary="Round trip",
        feature="outcomes-registry",
        inputs=(InputShape(shape="FeatureDeltaModel"),),
        output=OutputShape(shape="tuple[Violation, ...]"),
        keywords=("k1",),
        artifact="some/path.py",
        related=(),
        superseded_by=None,
    )

    # Read empty, append, write — then read again.
    initial = adapter.read_outcomes()
    assert initial == ()

    adapter.append_outcome(outcome)

    reloaded = adapter.read_outcomes()
    assert tuple(o.id for o in reloaded) == ("OUT-A",)

    # Schema version preserved on disk.
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == "0.1"
    assert len(raw["outcomes"]) == 1
    assert raw["outcomes"][0]["id"] == "OUT-A"


def test_yaml_registry_serializes_keys_in_canonical_order(tmp_path: Path) -> None:
    """Persisted entry exposes keys in the canonical sequence — independent of
    Python dict iteration order, this contract is the human-readability AC-1.c.

    Canonical order: id, kind, summary, feature, inputs, output, keywords,
    artifact, related, superseded_by.
    """
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        'schema_version: "0.1"\noutcomes: []\n',
        encoding="utf-8",
    )
    adapter = YamlRegistryAdapter(registry_path)
    adapter.append_outcome(
        Outcome(
            id="OUT-CANON",
            kind="specification",
            summary="canonical-order check",
            feature="outcomes-registry",
            inputs=(InputShape(shape="A"),),
            output=OutputShape(shape="B"),
            keywords=("kw",),
            artifact="some/path.py",
            related=(),
            superseded_by=None,
        )
    )

    raw_text = registry_path.read_text(encoding="utf-8")
    raw = yaml.safe_load(raw_text)
    entry_keys = tuple(raw["outcomes"][0].keys())
    assert entry_keys == (
        "id",
        "kind",
        "summary",
        "feature",
        "inputs",
        "output",
        "keywords",
        "artifact",
        "related",
        "superseded_by",
    )
    # Trailing newline preserved.
    assert raw_text.endswith("\n")
