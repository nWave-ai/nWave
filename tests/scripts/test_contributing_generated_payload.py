from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_contributing_identifies_generated_marketplace_payload() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    observations = {
        "canonical source trees": all(
            path in contributing for path in ("`nWave/`", "`src/des/`")
        ),
        "payload destination": "`plugins/nw/`" in contributing,
        "producer command": (
            "`python3 scripts/build_plugin.py --output-dir plugin/`" in contributing
        ),
        "direct-edit policy": "Do not edit `plugins/nw/` directly" in contributing,
    }

    missing = [name for name, observed in observations.items() if not observed]
    assert not missing, f"CONTRIBUTING.md lacks: {', '.join(missing)}"
